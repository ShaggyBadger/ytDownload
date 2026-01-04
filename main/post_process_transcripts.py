from tkinter import E
import db
import math, re, json, concurrent.futures, threading, os
from pathlib import Path
import subprocess
from sqlalchemy import or_
from utils import get_video_paths
from logger import setup_logger
import time, random

logger = setup_logger(__name__)

# --- Custom Exceptions ---
class GeminiQuotaExceededError(Exception):
    """Custom exception for when Gemini API quota limits are exceeded."""
    pass

# --- Helper Functions ---

def _call_gemini(prompt):
    """Runs the Gemini CLI with a given prompt, handling quota errors."""
    env = os.environ.copy()
    env['NO_BROWSER'] = 'true'
    result = subprocess.run(
        ["gemini", "-p", prompt],
        capture_output=True,
        text=True,
        check=False, # Do not raise CalledProcessError automatically
        env=env
    )

    if result.returncode != 0:
        error_message = result.stderr.strip()
        if "quota" in error_message.lower() or "limit" in error_message.lower():
            raise GeminiQuotaExceededError(f"Gemini API quota exceeded: {error_message}")
        else:
            raise RuntimeError(f"Gemini CLI error: {error_message}")
    return result.stdout.strip()

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

    except GeminiQuotaExceededError as e:
        logger.critical(f"!!! CRITICAL: Gemini API quota hit during {stage_name} for transcript {transcript_processing_id}. Stopping further LLM processing. Error: {e}")
        if stop_processing_flag is not None:
            stop_processing_flag[0] = True
        if db_session.is_active:
            db_session.rollback()
        if tp:
            tp.status = f"{stage_name.lower().replace(' ', '_')}_quota_exceeded"
            db_session.commit()
        # Re-raise to stop current transcript's processing
        raise RuntimeError(f"Processing halted due to Gemini API quota.") from e
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
        cleaned_text = _call_gemini(prompt)

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
    Logic for the metadata generation stage, using threading for parallel API calls.
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
        title = _call_gemini(prompt)
    metadata['title'] = title

    # 2. Get other metadata fields in parallel
    fields_to_generate = {
        "thesis": "a concise thesis statement",
        "outline": "a structured outline",
        "summary": "a brief summary"
    }

    # Helper function to be executed in each thread
    def _generate_field(field, description):
        logger.info(f"Generating '{field}'...")
        prompt = f"Please generate {description} for the following text:\n\n---\n\n{text_for_metadata}"
        try:
            result = _call_gemini(prompt)
            return field, result
        except RuntimeError as e:
            logger.error(f"Error generating '{field}': {e}")
            return field, f"Error generating '{field}'."

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(fields_to_generate)) as executor:
        # Submit all tasks to the thread pool
        future_to_field = {executor.submit(_generate_field, field, desc): field for field, desc in fields_to_generate.items()}

        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_field):
            field, result = future.result()
            metadata[field] = result

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
            cleaned_chunk = _call_gemini(prompt_disfluency)

            # 2b. Grammar Correction
            prompt_grammar = f"Please correct any grammar and spelling errors in the following text:\n\n{cleaned_chunk}"
            cleaned_chunk = _call_gemini(prompt_grammar)

            # 2c. Stylistic Enhancement
            prompt_style = f"Please improve the flow, clarity, and sentence structure of the following text to make it suitable for a book:\n\n{cleaned_chunk}"
            cleaned_chunk = _call_gemini(prompt_style)

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

class EditParagraphs:
    """Class to handle paragraph editing using Gemini API."""

    def __init__(self):
        """A class to handle paragraph-by-paragraph editing of a sermon."""
        self.sermon_selected = False # This can be used to track state if needed

    def select_sermon(self):
        """Selects and returns a sermon from the database for editing."""
        session = db.SessionLocal()
        try:
            sermons = session.query(db.TranscriptProcessing).filter(
                or_(
                    db.TranscriptProcessing.status == "metadata_generation_complete",
                    db.TranscriptProcessing.status == "sermon_export_complete"
                )
            ).all()

            if not sermons:
                logger.info("No sermons available for editing.")
                return None, None

            logger.info("Available Sermons for Editing:")
            for sermon in sermons:
                logger.info(f"ID: {sermon.id}, Status: {sermon.status}, Raw Transcript Path: {sermon.raw_transcript_path}")

            selected_id = input("Enter the ID of the sermon you want to edit: ")
            try:
                selected_id = int(selected_id)
            except ValueError:
                logger.error("Invalid input. Please enter a number.")
                return None, None

            selected_sermon = session.query(db.TranscriptProcessing).filter(db.TranscriptProcessing.id == selected_id).first()

            if not selected_sermon:
                logger.info(f"No sermon found with ID: {selected_id}")
                return None, None

            # Retrieve sermon text with paragraph breaks
            if not selected_sermon.secondary_cleaning_path:
                logger.error(f"Secondary cleaning path not found for sermon ID: {selected_id}")
                return None, None
            
            try:
                with open(selected_sermon.secondary_cleaning_path, 'r') as f:
                    transcript_text = f.read()
            except FileNotFoundError:
                logger.error(f"Sermon text file not found at {selected_sermon.secondary_cleaning_path}")
                return None, None
            except Exception as e:
                logger.error(f"Error reading sermon text file: {e}")
                return None, None

            # Retrieve outline from metadata
            if not selected_sermon.metadata_path:
                logger.error(f"Metadata path not found for sermon ID: {selected_id}")
                return None, None

            outline_data = None
            try:
                with open(selected_sermon.metadata_path, 'r') as f:
                    metadata = json.load(f)
                    outline_data = metadata.get('outline')
            except FileNotFoundError:
                logger.error(f"Metadata file not found at {selected_sermon.metadata_path}")
                return None, None
            except json.JSONDecodeError:
                logger.error(f"Error decoding JSON from metadata file at {selected_sermon.metadata_path}")
                return None, None
            except Exception as e:
                logger.error(f"Error reading or parsing metadata file: {e}")
                return None, None

            if not outline_data:
                logger.warning(f"Outline data not found in metadata for sermon ID: {selected_id}")
                return transcript_text, "" 

            return transcript_text, outline_data
        except Exception as e:
            logger.error(f"Error selecting sermon: {e}")
            return None, None
        finally:
            session.close()

    def _build_prompts_dictionary(self, transcript_text, outline):
        """Builds a dictionary of prompts for editing each paragraph."""
        # Initialize paths for prompts directory
        BASE_DIR = Path(__file__).resolve().parent
        PROMPTS_DIR = BASE_DIR / "prompts"

        # load prompt templates
        standard_prompt_path = PROMPTS_DIR / "edit-paragraph-standard.txt"
        first_paragraph_prompt_path = PROMPTS_DIR / "edit-paragraph-first.txt"
        last_paragraph_prompt_path = PROMPTS_DIR / "edit-paragraph-last.txt"

        paragraphs = transcript_text.split('\n\n')
        prompts_dictionary = {}
        total_paragraphs = len(paragraphs)

        for i, paragraph in enumerate(paragraphs):
            try:
                if i == 0:
                    prompt_template = first_paragraph_prompt_path.read_text()
                    prompt = prompt_template.format(
                        PARAGRAPH_TARGET=paragraph,
                        PARAGRAPH_NEXT=paragraphs[i + 1],
                        SERMON_OUTLINE=outline
                    )
                elif i == total_paragraphs - 1:
                    prompt_template = last_paragraph_prompt_path.read_text()
                    prompt = prompt_template.format(
                        PARAGRAPH_TARGET=paragraph,
                        PARAGRAPH_PREV=paragraphs[i - 1],
                        SERMON_OUTLINE=outline
                    )
                else:
                    prompt_template = standard_prompt_path.read_text()
                    prompt = prompt_template.format(
                        PARAGRAPH_TARGET=paragraph,
                        PARAGRAPH_PREV=paragraphs[i - 1],
                        PARAGRAPH_NEXT=paragraphs[i + 1],
                        SERMON_OUTLINE=outline
                    )
                prompts_dictionary[i] = {'prompt': prompt, 'original': paragraph}
            except FileNotFoundError as e:
                logger.error(f"Error reading prompt file: {e}")
                # Handle error, maybe skip this paragraph or use a default prompt
                prompts_dictionary[i] = {'prompt': '', 'original': paragraph}
            except Exception as e:
                logger.error(f"Error creating prompt for paragraph {i + 1}: {e}")
                prompts_dictionary[i] = {'prompt': '', 'original': paragraph}

        return prompts_dictionary

    def build_paragraph_editing_score(self, original_paragraph_dict, edited_paragraph_dict):
        """Compares original and edited paragraphs to build an editing score."""
        # build json file detaining the differences
        pass

    def edit_paragraphs(self, prompts_dictionary):
        """Processes a dictionary of prompts using multiple threads with retry logic."""
        edited_paragraphs = {} # holds edited paragraphs
        self.prompt_counter = 0
        self.lock = threading.Lock()
        stop_processing = [False]
        
        num_prompts = len(prompts_dictionary)

        def _edit_paragraph_worker():
            """Worker function for threads."""
            while self.prompt_counter < num_prompts:
                if stop_processing[0]:
                    break

                self.lock.acquire()
                if self.prompt_counter >= num_prompts:
                    self.lock.release()
                    break
                
                current_index = self.prompt_counter
                self.prompt_counter += 1
                self.lock.release()
                logger.debug(f"Thread processing paragraph index: {current_index}")

                prompt_data = prompts_dictionary.get(current_index)
                prompt = prompt_data.get('prompt')
                original_paragraph = prompt_data.get('original')
                
                if not prompt:
                    edited_paragraphs[current_index] = original_paragraph
                    continue

                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        edited_paragraph = _call_gemini(prompt)
                        edited_paragraphs[current_index] = edited_paragraph
                        if attempt > 0:
                            logger.info(f"Successfully processed prompt at index {current_index} on attempt {attempt + 1}.")
                        break # Success
                    except GeminiQuotaExceededError as e:
                        logger.critical(f"!!! CRITICAL: Gemini API quota hit. Halting all editing threads. Error: {e}.")
                        stop_processing[0] = True
                        edited_paragraphs[current_index] = original_paragraph
                        break # Stop retrying on quota error
                    except Exception as e:
                        logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for prompt at index {current_index}: {e}")
                        if attempt == max_retries - 1:
                            logger.error(f"All {max_retries} attempts failed for prompt at index {current_index}. Using original paragraph.")
                            edited_paragraphs[current_index] = original_paragraph
                
        threads = []
        for _ in range(min(num_prompts, 10)): # Use up to 10 threads
            thread = threading.Thread(target=_edit_paragraph_worker)
            threads.append(thread)
            thread.start()
            time.sleep(random.uniform(1.0, 2.0))  # stagger launches

        for thread in threads:
            thread.join()

        # Reassemble the edited paragraphs into a single text in the correct order
        edited_transcript_list = [edited_paragraphs.get(i, "") for i in range(num_prompts)]
        edited_transcript = "\n\n".join(edited_transcript_list)
        
        return edited_transcript

    def run_editor(self):
        """Orchestrates the sermon editing process."""
        transcript_text, outline = self.select_sermon()

        if transcript_text and outline is not None:
            # build prompts dictionary
            logger.info("Building prompts dictionary...")
            prompts = self._build_prompts_dictionary(transcript_text, outline)
            logger.info(f"Built prompts for {len(prompts)} paragraphs.")
            
            # edit paragraphs
            logger.info("Starting sermon editing process...")
            edited_transcript = self.edit_paragraphs(prompts)
            logger.info("Sermon editing process complete.")

            # save edited transcript to file
            
            return edited_transcript
        else:
            logger.info("Sermon editing process aborted.")
            return None

if __name__ == "__main__":
    # TODO: build some kind of llm check to compare the raw and the edited versions? maybe use ollama?? 
    # TODO: add option to save edited transcript back to DB/file system
    editor = EditParagraphs()
    edited_text = editor.run_editor()
    print("\n--- Edited Sermon Transcript ---\n")
    print(edited_text)