from tkinter import E
from joshlib.ollama import OllamaClient
import db
import math, re, json, os
from pathlib import Path
import subprocess
from sqlalchemy import or_
# from main import ollama_client
from utils import get_video_paths
from logger import setup_logger
import time

logger = setup_logger(__name__)

# --- Custom Exceptions ---
class GeminiQuotaExceededError(Exception):
    """Custom exception for when Gemini API quota limits are exceeded."""
    pass

# --- Helper Functions ---

def _get_video_duration_str(db_session, video_id):
    """Fetches and formats the trimmed duration of a video."""
    video = db_session.query(db.Video).filter(db.Video.id == video_id).first()
    if video and video.end_time and video.start_time:
        duration = video.end_time - video.start_time
        return f"{duration // 60} minutes, {duration % 60} seconds"
    return "Unknown"

# --- Centralized Processing Logic ---

def _execute_processing_stage(transcript_processing_id, stage_logic_func, success_status, stage_name, current_index=None, total_count=None, stop_processing_flag=None):
    """
    A helper function to manage the boilerplate of a processing stage.
    - Opens a DB session.
    - Fetches the transcript processing object.
    - Executes the provided stage logic.
    - Handles success, errors, and session closing.
    """
    db_session = db.SessionLocal()
    tp = None
    try:
        tp = db_session.query(db.TranscriptProcessing).filter(db.TranscriptProcessing.id == transcript_processing_id).first()
        if not tp:
            logger.error(f"No transcript processing entry found with id: {transcript_processing_id}")
            return

        progress_str = ""
        if current_index is not None and total_count is not None:
            progress_str = f" ({current_index}/{total_count})"
        
        logger.info(f"Beginning {stage_name} for transcript {tp.id}{progress_str}...")

        # Execute the specific logic for this stage
        stage_logic_func(tp, db_session)

        # Update status and commit
        tp.status = success_status
        db_session.commit()
        logger.info(f"{stage_name} complete for transcript: {tp.id}")

    except OllamaProcessingError as e:
        logger.critical(f"!!! CRITICAL: Ollama API processing issue during {stage_name} for transcript {transcript_processing_id}. Stopping further LLM processing. Error: {e}")
        if stop_processing_flag is not None:
            stop_processing_flag[0] = True
        if db_session.is_active:
            db_session.rollback()
        if tp:
            tp.status = f"{stage_name.lower().replace(' ', '_')}_ollama_failed"
            db_session.commit()
        # Re-raise to stop current transcript's processing
        raise RuntimeError(f"Processing halted due to Ollama API processing issue.") from e
    except Exception as e:
        logger.error(f"Error during {stage_name} for transcript {transcript_processing_id}: {e}")
        if db_session.is_active:
            db_session.rollback()
        if tp:
            tp.status = f"{stage_name.lower().replace(' ', '_')}_failed"
            db_session.commit()
        # Re-raise to stop current transcript's processing
        raise RuntimeError(f"Processing halted due to unexpected error.") from e
    finally:
        db_session.close()

def _initial_cleaning_logic(tp, db_session):
    """
    Logic for the initial cleaning stage.
    """
    # Read the raw transcript
    with open(tp.raw_transcript_path, 'r') as f:
        raw_text = f.read()

    # Perform initial cleaning (example: remove extra whitespace)
    cleaned_text = " ".join(raw_text.split())

    # Write the cleaned text to a new file
    initial_cleaning_path = Path(tp.raw_transcript_path).with_suffix('.initial.txt')
    with open(initial_cleaning_path, 'w') as f:
        f.write(cleaned_text)

    # Update the database
    tp.initial_cleaning_path = str(initial_cleaning_path)

def initial_cleaning(transcript_processing_id, current_index=None, total_count=None, stop_processing_flag=None):
    """
    Public-facing function for the initial cleaning stage.
    """
    _execute_processing_stage(
        transcript_processing_id,
        _initial_cleaning_logic,
        "initial_cleaning_complete",
        "Initial Cleaning",
        current_index=current_index,
        total_count=total_count,
        stop_processing_flag=stop_processing_flag
    )

def _secondary_cleaning_logic(tp, db_session):
    """
    Logic for the secondary cleaning stage.
    """
    # Read the initially cleaned transcript
    with open(tp.initial_cleaning_path, 'r') as f:
        initial_text = f.read()

    # Calculate initial word count
    initial_word_count = len(initial_text.split())

    # Create a prompt for the LLM
    prompt = f"Please add paragraph breaks to the following text:\n\n{initial_text}"

    text_to_save = initial_text  # Default to initial text
    max_retries = 3

    for attempt in range(max_retries):
        logger.info(f"Secondary cleaning attempt {attempt + 1}/{max_retries} for transcript {tp.id}...")
        
        # Call the LLM to add paragraph breaks
        cleaned_text = ollama_processor.call_ollama(prompt)

        # Calculate cleaned text word count
        cleaned_word_count = len(cleaned_text.split())

        # Determine word count loss
        word_loss_percentage = 0.0
        if initial_word_count > 0: # Avoid division by zero
            word_loss_percentage = (abs(initial_word_count - cleaned_word_count) / initial_word_count) * 100

        if word_loss_percentage <= 2.0: # 2% threshold
            logger.info(f"Secondary cleaning word count change: {word_loss_percentage:.2f}%. Acceptable.")
            text_to_save = cleaned_text
            break  # Exit loop on success
        else:
            logger.warning(f"Warning: Attempt {attempt + 1} resulted in a {word_loss_percentage:.2f}% word count loss. Retrying...")

        if attempt == max_retries - 1:
            logger.warning(f"Warning: All {max_retries} secondary cleaning attempts resulted in high word count loss for transcript {tp.id}. Falling back to initial text.")

    # Write the chosen text to a new file
    secondary_cleaning_path = Path(tp.raw_transcript_path).with_suffix('.secondary.txt')
    with open(secondary_cleaning_path, 'w') as f:
        f.write(text_to_save)

    # Update the database
    tp.secondary_cleaning_path = str(secondary_cleaning_path)

def secondary_cleaning(transcript_processing_id, current_index=None, total_count=None, stop_processing_flag=None):
    """
    Public-facing function for the secondary cleaning stage.
    """
    _execute_processing_stage(
        transcript_processing_id,
        _secondary_cleaning_logic,
        "secondary_cleaning_complete",
        "Secondary Cleaning",
        current_index=current_index,
        total_count=total_count,
        stop_processing_flag=stop_processing_flag
    )

def _gen_metadata_logic(tp, db_session):
    """
    Logic for the metadata generation stage, processing fields sequentially.
    """
    with open(tp.secondary_cleaning_path, 'r') as f:
        text_for_metadata = f.read()

    metadata = {}

    # 1. Get Title (sequentially, as it's a single call with custom logic)
    title = None
    match = re.search(r"The title of todays sermon is (.*?)[\.\n]", text_for_metadata, re.IGNORECASE)
    if match:
        title = match.group(1).strip()
    else:
        logger.info("Generating 'title'...")
        prompt = f"Please provide a single, concise, and suitable title for the following text. Do not include any introductory phrases or bullet points. Just the title itself.\n\n---\n\n{text_for_metadata}"
        title = ollama_processor.call_ollama(prompt)
    metadata['title'] = title

    # 2. Get other metadata fields sequentially
    fields_to_generate = {
        "thesis": "a concise thesis statement",
        "outline": "a structured outline",
        "summary": "a brief summary"
    }

    for field, description in fields_to_generate.items():
        logger.info(f"Generating '{field}'...")
        prompt = f"Please generate {description} for the following text:\n\n---\n\n{text_for_metadata}"
        try:
            result = ollama_processor.call_ollama(prompt)
            metadata[field] = result
        except RuntimeError as e:
            logger.error(f"Error generating '{field}': {e}")
            metadata[field] = f"Error generating '{field}'."

    # 3. Write to file as JSON
    metadata_path = Path(tp.raw_transcript_path).with_suffix('.meta.txt')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=4)

    tp.metadata_path = str(metadata_path)

def gen_metadata(transcript_processing_id, current_index=None, total_count=None, stop_processing_flag=None):
    """
    Public-facing function for the metadata generation stage.
    """
    _execute_processing_stage(
        transcript_processing_id,
        _gen_metadata_logic,
        "metadata_generation_complete",
        "Metadata Generation",
        current_index=current_index,
        total_count=total_count,
        stop_processing_flag=stop_processing_flag
    )

def _final_pass_logic(tp, db_session):
    """
    Logic for the final pass stage.
    """
    # Read the secondarily cleaned transcript
    with open(tp.secondary_cleaning_path, 'r') as f:
        secondary_text = f.read()

    # Perform final pass (example: convert to lowercase)
    cleaned_text = secondary_text.lower()

    # Calculate the final word count
    final_word_count = len(cleaned_text.split())

    # Write the cleaned text to a new file
    final_pass_path = Path(tp.raw_transcript_path).with_suffix('.final.txt')
    with open(final_pass_path, 'w') as f:
        f.write(cleaned_text)

    # Update the database
    tp.final_pass_path = str(final_pass_path)
    tp.final_word_count = final_word_count

def final_pass(transcript_processing_id):
    """
    Public-facing function for the final pass stage.
    """
    _execute_processing_stage(
        transcript_processing_id,
        _final_pass_logic,
        "final_pass_complete",
        "Final Pass"
    )

def _python_scrub_logic(tp, db_session):
    """
    Logic for the python_scrub stage.
    """
    # Read the initial cleaning transcript
    with open(tp.initial_cleaning_path, 'r') as f:
        initial_cleaning_text = f.read()

    # Perform python_scrub (example: remove all instances of the word "the")
    cleaned_text = initial_cleaning_text.replace(" the ", " ")

    # Write the cleaned text to a new file
    python_scrub_path = Path(tp.raw_transcript_path).with_suffix('.scrubbed.txt')
    with open(python_scrub_path, 'w') as f:
        f.write(cleaned_text)

    # Update the database
    tp.python_scrub_path = str(python_scrub_path)

def python_scrub(transcript_processing_id):
    """
    Public-facing function for the python_scrub stage.
    """
    _execute_processing_stage(
        transcript_processing_id,
        _python_scrub_logic,
        "python_scrub_complete",
        "Python Scrub"
    )

def _llm_book_cleanup_logic(tp, db_session):
    """
    Logic for the LLM book cleanup stage.
    """
    with open(tp.python_scrub_path, 'r') as f:
        text_to_clean = f.read()

    # 1. Chunk the text
    paragraphs = text_to_clean.split('\n\n')
    chunks = []
    current_chunk = ""
    for p in paragraphs:
        if len(current_chunk.split()) + len(p.split()) < 1000:
            current_chunk += p + "\n\n"
        else:
            chunks.append(current_chunk)
            current_chunk = p + "\n\n"
    chunks.append(current_chunk)

    cleaned_chunks = []
    for i, chunk in enumerate(chunks):
        logger.info(f"Processing chunk {i+1}/{len(chunks)}...")
        try:
            # 2a. Disfluency Removal
            prompt_disfluency = f"Please remove filler words like 'um', 'ah', and 'you know' from the following text:\n\n{chunk}"
            cleaned_chunk = ollama_processor.call_ollama(prompt_disfluency)

            # 2b. Grammar Correction
            prompt_grammar = f"Please correct any grammar and spelling errors in the following text:\n\n{cleaned_chunk}"
            cleaned_chunk = ollama_processor.call_ollama(prompt_grammar)

            # 2c. Stylistic Enhancement
            prompt_style = f"Please improve the flow, clarity, and sentence structure of the following text to make it suitable for a book:\n\n{cleaned_chunk}"
            cleaned_chunk = ollama_processor.call_ollama(prompt_style)

            cleaned_chunks.append(cleaned_chunk)
        except RuntimeError as e:
            logger.error(f"Error processing chunk {i+1} for transcript {tp.id}: {e}")
            raise e

    # 3. Reassemble the sermon
    final_text = "\n\n".join(cleaned_chunks)

    # 4. Save and Update
    book_ready_path = Path(tp.raw_transcript_path).with_suffix('.book.txt')
    with open(book_ready_path, 'w') as f:
        f.write(final_text)

    tp.book_ready_path = str(book_ready_path)

def llm_book_cleanup(transcript_processing_id):
    """
    Public-facing function for the LLM book cleanup stage.
    """
    _execute_processing_stage(
        transcript_processing_id,
        _llm_book_cleanup_logic,
        "book_ready_complete",
        "LLM Book Cleanup"
    )

def _update_metadata_file_logic(tp, db_session):
    """
    Logic for the update metadata file stage.
    """
    if not tp.book_ready_path or not tp.metadata_path:
        logger.error(f"Missing paths for transcript processing id: {tp.id}")
        return

    # 1. Read existing metadata
    with open(tp.metadata_path, 'r') as f:
        try:
            metadata = json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Warning: Could not parse JSON from {tp.metadata_path}. Starting with an empty metadata object.")
            metadata = {}


    # 2. Calculate word count
    with open(tp.book_ready_path, 'r') as f:
        book_text = f.read()
    word_count = len(book_text.split())

    # 3. Get video duration
    duration_str = _get_video_duration_str(db_session, tp.video_id)

    # 4. Add new data
    metadata['final_word_count'] = word_count
    metadata['trimmed_video_duration'] = duration_str

    # 5. Write updated metadata back to file
    with open(tp.metadata_path, 'w') as f:
        json.dump(metadata, f, indent=4)

def update_metadata_file(transcript_processing_id):
    """
    Public-facing function for the update metadata file stage.
    """
    _execute_processing_stage(
        transcript_processing_id,
        _update_metadata_file_logic,
        "metadata_updated",
        "Update Metadata File"
    )

import sermon_exporter # Add this import
import argparse # Add this import

# ... existing code ...

def _export_sermon_file_logic(tp, db_session):
    """
    Logic for the sermon export file generation stage.
    """
    # Simply call the new function from sermon_exporter
    sermon_exporter.export_single_sermon(tp.id)
    # The sermon_exporter function prints its own success/error messages

def export_sermon_file(transcript_processing_id, current_index=None, total_count=None, stop_processing_flag=None):
    """
    Public-facing function for the sermon export file generation stage.
    """
    _execute_processing_stage(
        transcript_processing_id,
        _export_sermon_file_logic,
        "sermon_export_complete",
        "Sermon Export",
        current_index=current_index,
        total_count=total_count,
        stop_processing_flag=stop_processing_flag
    )

def reset_transcript_status(transcript_id, db_session):
    """
    Resets the status of a transcript and its associated video in the database.
    This function does NOT delete any files.
    """
    logger.info(f"--- Resetting status for transcript ID: {transcript_id} ---")

    transcript = db_session.query(db.TranscriptProcessing).filter(db.TranscriptProcessing.id == transcript_id).first()
    if not transcript:
        logger.error(f"No transcript processing entry found with id: {transcript_id}")
        return

    # Reset status on TranscriptProcessing
    transcript.book_ready_path = None
    transcript.final_pass_path = None
    transcript.metadata_path = None
    transcript.initial_cleaning_path = None
    transcript.secondary_cleaning_path = None
    transcript.python_scrub_path = None 
    transcript.status = "raw_transcript_received"

    # Also reset status on the Video table
    video = db_session.query(db.Video).filter(db.Video.id == transcript.video_id).first()
    if video:
        logger.info(f"Resetting video status for video ID: {video.id}")
        video.stage_4_status = "pending"
        video.stage_5_status = "pending"
        video.stage_6_status = "pending"
    else:
        logger.error(f"Could not find matching video for transcript ID: {transcript_id}")
    
    db_session.commit()
    logger.info(f"Transcript ID: {transcript_id} has been reset and is ready for reprocessing.")

# --- Main Orchestration ---

def post_process_transcripts():
    """
    Main function to orchestrate the post-processing of transcripts
    by advancing them through all stages for each transcript.
    """
    logger.info("--- Starting Transcript Post-Processing ---")
    db_session = db.SessionLocal()
    stop_processing = [False] # Initialize stop flag
    try:
        # Find all transcripts that need processing from the start
        # This will get all transcripts that are not yet fully exported.
        transcripts_to_process = db_session.query(db.TranscriptProcessing).filter(
            db.TranscriptProcessing.status.in_([
                "raw_transcript_received",
                "initial_cleaning_complete",
                "secondary_cleaning_complete",
                "metadata_generation_complete"
            ])
        ).order_by(db.TranscriptProcessing.id).all()
        
        total_transcripts = len(transcripts_to_process)
        logger.info(f"Found {total_transcripts} transcripts to process through the pipeline.")

        for i, tp in enumerate(transcripts_to_process):
            if stop_processing[0]:
                logger.warning("Processing halted due to Gemini API quota or other error.")
                break
            
            logger.info(f"--- Processing Transcript: {tp.id} ({i + 1}/{total_transcripts}) ---")

            # 1. Initial Cleaning
            try:
                if not stop_processing[0] and tp.status == "raw_transcript_received":
                    initial_cleaning(tp.id, current_index=i + 1, total_count=total_transcripts, stop_processing_flag=stop_processing)
                    db_session.refresh(tp) # Refresh tp object to get updated status
            except RuntimeError: pass

            # 2. Secondary Cleaning
            try:
                if not stop_processing[0] and tp.status == "initial_cleaning_complete":
                    secondary_cleaning(tp.id, current_index=i + 1, total_count=total_transcripts, stop_processing_flag=stop_processing)
                    db_session.refresh(tp) # Refresh tp object to get updated status
            except RuntimeError: pass

            # 3. Metadata Generation
            try:
                if not stop_processing[0] and tp.status == "secondary_cleaning_complete":
                    gen_metadata(tp.id, current_index=i + 1, total_count=total_transcripts, stop_processing_flag=stop_processing)
                    db_session.refresh(tp) # Refresh tp object to get updated status
            except RuntimeError: pass

            # 4. Sermon Export File Generation
            try:
                if not stop_processing[0] and tp.status == "metadata_generation_complete":
                    export_sermon_file(tp.id, current_index=i + 1, total_count=total_transcripts, stop_processing_flag=stop_processing)
                    db_session.refresh(tp) # Refresh tp object to get updated status
            except RuntimeError: pass
            
    finally:
        db_session.close()
        
    # After all other stages, run the final automated editing process
    run_automated_paragraph_editing()

def run_automated_paragraph_editing():
    """
    Finds all sermons ready for the final edit and processes them automatically
    in sequential order.
    """
    logger.info("--- Starting Automated Final Paragraph Editing ---")
    session = db.SessionLocal()
    try:
        sermons_to_process = session.query(db.TranscriptProcessing).filter(
            db.TranscriptProcessing.status == "sermon_export_complete"
        ).order_by(db.TranscriptProcessing.id).all()

        if not sermons_to_process:
            logger.info("No sermons are ready for the final automated edit.")
            return

        logger.info(f"Found {len(sermons_to_process)} sermons to process for final edit.")
        editor = EditParagraphs()
        num_threads = 1 # Always run sequentially in automation

        for i, sermon in enumerate(sermons_to_process):
            logger.info(f"--- Processing Sermon {i+1}/{len(sermons_to_process)} (ID: {sermon.id}) for final edit ---")

            # 1. Retrieve sermon text
            if not sermon.secondary_cleaning_path:
                logger.error(f"Secondary cleaning path not found for sermon ID: {sermon.id}. Skipping.")
                continue
            try:
                with open(sermon.secondary_cleaning_path, 'r') as f:
                    transcript_text = f.read()
            except FileNotFoundError:
                logger.error(f"Sermon text file not found at {sermon.secondary_cleaning_path}. Skipping.")
                continue

            # 2. Retrieve outline from metadata
            outline_data = ""
            if sermon.metadata_path:
                try:
                    with open(sermon.metadata_path, 'r') as f:
                        metadata = json.load(f)
                        outline_data = metadata.get('outline', '')
                except (FileNotFoundError, json.JSONDecodeError):
                    pass # Warnings will be logged by the editor class if needed

            # 3. Prepare paragraph data
            paragraph_file_path = editor._get_paragraph_file_path(sermon)
            if not paragraph_file_path:
                logger.error(f"Could not determine path for paragraphs.json for sermon {sermon.id}. Skipping.")
                continue

            paragraphs_data = None
            if paragraph_file_path.exists():
                try:
                    with open(paragraph_file_path, 'r') as f:
                        paragraphs_data = json.load(f)
                except (json.JSONDecodeError, IOError):
                    pass # Will be handled by the next block
            
            if not paragraphs_data:
                paragraphs_data = editor._build_paragraphs_json_data(transcript_text, outline_data)
                editor._save_paragraphs_to_file(paragraphs_data, paragraph_file_path)

            # 4. Start the editing process
            edited_transcript = editor.edit_paragraphs(paragraphs_data, paragraph_file_path)

            if edited_transcript:
                final_transcript_path = Path(sermon.raw_transcript_path).with_suffix('.edited.txt')
                try:
                    with open(final_transcript_path, 'w') as f:
                        f.write(edited_transcript)
                    logger.info(f"Successfully saved final edited transcript to: {final_transcript_path}")
                    
                    # 5. Update status
                    sermon.status = 'final_edit_complete'
                    session.commit()
                    logger.info(f"Updated status to 'final_edit_complete' for sermon {sermon.id}")

                except IOError as e:
                    logger.error(f"Error saving final transcript for sermon {sermon.id}: {e}")
                    session.rollback()
        
        logger.info("--- Automated final paragraph editing complete. ---")

    except Exception as e:
        logger.error(f"An unexpected error occurred during automated editing: {e}")
        session.rollback()
    finally:
        session.close()

class EditParagraphs:
    """Class to handle paragraph editing using Gemini API."""

    def __init__(self):
        """A class to handle paragraph-by-paragraph editing of a sermon."""
        self.sermon_selected = False # This can be used to track state if needed
        self.ollama_client = OllamaClient()


    def select_sermon(self):
        """Selects and returns a list of sermon objects for editing."""
        session = db.SessionLocal()
        try:
            sermons = session.query(db.TranscriptProcessing).filter(
                or_(
                    db.TranscriptProcessing.status == "metadata_generation_complete",
                    db.TranscriptProcessing.status == "sermon_export_complete"
                )
            ).order_by(db.TranscriptProcessing.id).all()

            if not sermons:
                logger.info("No sermons available for editing.")
                return []

            logger.info("Available Sermons for Editing:")
            for sermon in sermons:
                logger.info(f"ID: {sermon.id}, Status: {sermon.status}, Path: {sermon.raw_transcript_path}")

            selected_id_str = input("Enter the ID of the sermon you want to edit (or 'all' to process all, or 'reset <ID>', or 'reset all'): ")
            
            if selected_id_str.lower() == 'reset all':
                return self._reset_all_sermons_editing_state()

            if selected_id_str.lower().startswith('reset '):
                try:
                    reset_id = int(selected_id_str.split(' ')[1])
                    return self._reset_sermon_editing_state(reset_id) # Return a flag for reset action
                except (ValueError, IndexError):
                    logger.error("Invalid reset command. Use 'reset <ID>'.")
                    return []
            
            if selected_id_str.lower() == 'all':
                return sermons

            try:
                selected_id = int(selected_id_str)
                selected_sermon = next((s for s in sermons if s.id == selected_id), None)
                if selected_sermon:
                    return [selected_sermon]
                else:
                    logger.info(f"No sermon found with ID: {selected_id}")
                    return []
            except ValueError:
                logger.error("Invalid input. Please enter a number, 'all', or 'reset <ID>'.")
                return []

        except Exception as e:
            logger.error(f"An unexpected error occurred in select_sermon: {e}")
            return []
        finally:
            session.close()

    def _reset_sermon_editing_state(self, sermon_id):
        """Resets the editing state for a given sermon."""
        session = db.SessionLocal()
        try:
            sermon = session.query(db.TranscriptProcessing).filter(db.TranscriptProcessing.id == sermon_id).first()
            if not sermon:
                logger.info(f"No sermon found with ID: {sermon_id} to reset.")
                return "RESET_FAILED"

            # Delete paragraphs.json file
            paragraph_file_path = self._get_paragraph_file_path(sermon)
            if paragraph_file_path and paragraph_file_path.exists():
                os.remove(paragraph_file_path)
                logger.info(f"Deleted {paragraph_file_path} for sermon ID: {sermon_id}")
            else:
                logger.info(f"No paragraphs.json found for sermon ID: {sermon_id} at {paragraph_file_path}. Nothing to delete.")

            # Reset status in DB
            sermon.status = "sermon_export_complete" # Or a custom 'editing_reset' status if desired
            session.commit()
            logger.info(f"Reset status of sermon ID: {sermon_id} to 'sermon_export_complete'. It can now be re-edited.")
            return "RESET_ACTION" # Indicate that a reset occurred

        except Exception as e:
            logger.error(f"Error resetting sermon ID {sermon_id}: {e}")
            session.rollback()
            return "RESET_FAILED"
        finally:
            session.close()

    def _reset_all_sermons_editing_state(self):
        """Resets the editing state for all available sermons."""
        session = db.SessionLocal()
        try:
            sermons_to_reset = session.query(db.TranscriptProcessing).filter(
                or_(
                    db.TranscriptProcessing.status == "metadata_generation_complete",
                    db.TranscriptProcessing.status == "sermon_export_complete"
                )
            ).all()

            if not sermons_to_reset:
                logger.info("No sermons found in a resettable state.")
                return "RESET_FAILED"

            logger.info(f"Found {len(sermons_to_reset)} sermons to reset.")
            for sermon in sermons_to_reset:
                self._reset_sermon_editing_state(sermon.id)
            
            logger.info("All available sermons have been reset.")
            return "RESET_ACTION"

        except Exception as e:
            logger.error(f"An error occurred while resetting all sermons: {e}")
            session.rollback()
            return "RESET_FAILED"
        finally:
            session.close()

    def _get_paragraph_file_path(self, selected_sermon):
        """Returns the path for the paragraphs.json file for a given sermon."""
        if not selected_sermon or not selected_sermon.raw_transcript_path:
            return None
        return Path(selected_sermon.raw_transcript_path).parent / "paragraphs.json"

    def _build_paragraphs_json_data(self, transcript_text, outline):
        """Builds the initial data structure for paragraphs.json."""
        # Initialize paths for prompts directory
        BASE_DIR = Path(__file__).resolve().parent
        PROMPTS_DIR = BASE_DIR / "prompts"

        # load prompt templates
        standard_prompt_path = PROMPTS_DIR / "edit-paragraph-standard.txt"
        first_paragraph_prompt_path = PROMPTS_DIR / "edit-paragraph-first.txt"
        last_paragraph_prompt_path = PROMPTS_DIR / "edit-paragraph-last.txt"

        paragraphs = transcript_text.split('\n\n')
        paragraphs_data = []
        total_paragraphs = len(paragraphs)

        for i, paragraph in enumerate(paragraphs):
            prompt = ""
            try:
                if i == 0 and total_paragraphs > 1:
                    prompt_template = first_paragraph_prompt_path.read_text()
                    prompt = prompt_template.format(PARAGRAPH_TARGET=paragraph, PARAGRAPH_NEXT=paragraphs[i + 1])
                elif i == total_paragraphs - 1 and total_paragraphs > 1:
                    prompt_template = last_paragraph_prompt_path.read_text()
                    prompt = prompt_template.format(PARAGRAPH_TARGET=paragraph, PARAGRAPH_PREV=paragraphs[i - 1])
                elif total_paragraphs > 1:
                    prompt_template = standard_prompt_path.read_text()
                    prompt = prompt_template.format(PARAGRAPH_TARGET=paragraph, PARAGRAPH_PREV=paragraphs[i - 1], PARAGRAPH_NEXT=paragraphs[i + 1])
                else: # Handle case with only one paragraph
                    prompt_template = first_paragraph_prompt_path.read_text() # Or a specific single-paragraph prompt
                    prompt = prompt_template.format(PARAGRAPH_TARGET=paragraph, PARAGRAPH_NEXT="")


                paragraph_entry = {
                    'index': i,
                    'original': paragraph,
                    'prompt': prompt,
                    'edited': None
                }
                paragraphs_data.append(paragraph_entry)

            except FileNotFoundError as e:
                logger.error(f"Error reading prompt file: {e}")
                paragraphs_data.append({'index': i, 'original': paragraph, 'prompt': '', 'edited': None})
            except Exception as e:
                logger.error(f"Error creating prompt for paragraph {i + 1}: {e}")
                paragraphs_data.append({'index': i, 'original': paragraph, 'prompt': '', 'edited': None})

        return paragraphs_data

    def build_paragraph_editing_score(self, original_paragraph_dict, edited_paragraph_dict):
        """Compares original and edited paragraphs to build an editing score."""
        # build json file detaining the differences
        pass

    def _save_paragraphs_to_file(self, data, file_path):
        """Saves the paragraph data to the JSON file."""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save progress to {file_path}: {e}")

    def edit_paragraphs(self, paragraphs_data, paragraph_file_path):
        """Processes paragraphs that need editing and saves progress intermittently."""
        
        # Filter to get only the paragraphs that need editing
        paragraphs_to_process = [p for p in paragraphs_data if p.get('edited') is None]
        num_to_process = len(paragraphs_to_process)

        if num_to_process == 0:
            logger.info("All paragraphs have already been edited.")
            # Reassemble the full transcript from the loaded data
            edited_transcript = "\n\n".join(p.get('edited', p.get('original', '')) for p in paragraphs_data)
            return edited_transcript

        logger.info(f"Starting sequential processing of {num_to_process} remaining paragraphs...")
        
        for i, paragraph_item in enumerate(paragraphs_to_process):
            index = paragraph_item.get('index')
            prompt = paragraph_item.get('prompt')
            original_paragraph = paragraph_item.get('original')

            logger.info(f"Processing paragraph {index + 1}/{len(paragraphs_data)} ({i + 1}/{num_to_process} in this run).")

            if not prompt:
                logger.warning(f"No prompt for paragraph {index}. Using original.")
                paragraph_item['edited'] = original_paragraph
                self._save_paragraphs_to_file(paragraphs_data, paragraph_file_path)
                continue

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    edited_text = self.ollama_client.submit_prompt(prompt)
                    #ollama_processor.call_ollama(prompt, timeout=300)
                    if attempt > 0:
                        logger.info(f"Successfully processed paragraph {index} on attempt {attempt + 1}.")
                    
                    # Update the shared data structure
                    paragraph_item['edited'] = edited_text
                    # Save progress
                    self._save_paragraphs_to_file(paragraphs_data, paragraph_file_path)
                    break # Exit retry loop on success

                except OllamaProcessingError as e:
                    logger.critical(f"!!! CRITICAL: Ollama API processing issue. Halting all editing. Error: {e}.")
                    return None # Stop editing and return early

                except RuntimeError as e:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for paragraph {index}: {e}")
                    if attempt == max_retries - 1:
                        logger.error(f"All {max_retries} attempts failed for paragraph {index}. Original will be used implicitly (edited=None).")
                        # No break here, allows loop to finish without setting 'edited'
                        
        logger.info("Paragraph processing run complete.")
        
        # Final reassembly of the transcript
        # Use 'edited' if available, otherwise fall back to 'original'
        edited_transcript_list = []
        for p in sorted(paragraphs_data, key=lambda x: x['index']):
            if p.get('edited') is not None:
                edited_transcript_list.append(p['edited'])
            else:
                logger.warning(f"Using original text for paragraph {p['index']} as it was not successfully edited.")
                edited_transcript_list.append(p['original'])

        return "\n\n".join(edited_transcript_list)

    def run_editor(self):
        """Orchestrates the sermon editing process for one or more sermons with resumability."""
        sermons_to_process = self.select_sermon()

        if sermons_to_process in ["RESET_ACTION", "RESET_FAILED"]:
            logger.info("Sermon editing state reset or failed. Aborting further editing.")
            return
        if not sermons_to_process:
            logger.info("No sermons selected for editing. Aborting.")
            return

        # Since run_editor can process one or more sermons, we loop through them.
        # We will return the text of the *last* processed sermon for printing.
        final_edited_text = None
        session = db.SessionLocal()
        
        try:
            for i, sermon in enumerate(sermons_to_process):
                logger.info(f"--- Processing Sermon {i+1}/{len(sermons_to_process)} (ID: {sermon.id}) ---")

                # 1. Retrieve sermon text
                if not sermon.secondary_cleaning_path or not Path(sermon.secondary_cleaning_path).exists():
                    logger.error(f"Secondary cleaning path not found for sermon ID: {sermon.id}. Skipping.")
                    continue
                with open(sermon.secondary_cleaning_path, 'r') as f:
                    transcript_text = f.read()

                # 2. Retrieve outline from metadata
                outline_data = ""
                if sermon.metadata_path and Path(sermon.metadata_path).exists():
                    with open(sermon.metadata_path, 'r') as f:
                        metadata = json.load(f)
                        outline_data = metadata.get('outline', '')

                # 3. Prepare paragraph data
                paragraph_file_path = self._get_paragraph_file_path(sermon)
                paragraphs_data = None
                if paragraph_file_path.exists():
                    with open(paragraph_file_path, 'r') as f:
                        paragraphs_data = json.load(f)
                
                if not paragraphs_data:
                    paragraphs_data = self._build_paragraphs_json_data(transcript_text, outline_data)
                    self._save_paragraphs_to_file(paragraphs_data, paragraph_file_path)

                # 4. Start the editing process
                edited_transcript = self.edit_paragraphs(paragraphs_data, paragraph_file_path)

                if edited_transcript:
                    final_transcript_path = Path(sermon.raw_transcript_path).with_suffix('.edited.txt')
                    with open(final_transcript_path, 'w') as f:
                        f.write(edited_transcript)
                    logger.info(f"Successfully saved final edited transcript to: {final_transcript_path}")
                    
                    # 5. Update status
                    # Re-fetch the sermon object within this session to avoid detached instance error
                    sermon_in_session = session.query(db.TranscriptProcessing).filter(db.TranscriptProcessing.id == sermon.id).first()
                    if sermon_in_session:
                        sermon_in_session.status = 'final_edit_complete'
                        session.commit()
                        logger.info(f"Updated status to 'final_edit_complete' for sermon {sermon.id}")
                    
                    final_edited_text = edited_transcript # Keep track of the last edited text
                else:
                    logger.error(f"Editing failed for sermon {sermon.id}. No transcript was returned.")
                
                return final_edited_text

        except Exception as e:
            logger.error(f"An unexpected error occurred during automated editing: {e}")
            session.rollback()
        finally:
            session.close()
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage transcript post-processing.")
    parser.add_argument("--reset", type=int, help="Reset the processing status for a given transcript ID.")

    args = parser.parse_args()

    if args.reset:
        session = db.SessionLocal()
        try:
            reset_transcript_status(args.reset, session)
        finally:
            session.close()
    else:
        # Existing main execution for EditParagraphs, if any
        # TODO: build some kind of llm check to compare the raw and the edited versions? maybe use ollama?? 
        # TODO: add option to save edited transcript back to DB/file system
        editor = EditParagraphs()
        edited_text = editor.run_editor()
        print("\n--- Edited Sermon Transcript ---\n")
        print(edited_text)