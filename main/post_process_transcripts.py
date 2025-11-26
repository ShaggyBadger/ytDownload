import db
import math, re, json
from pathlib import Path
import subprocess
from sqlalchemy import or_
from utils import get_video_paths # <--- Added import

# --- Custom Exceptions ---
class GeminiQuotaExceededError(Exception):
    """Custom exception for when Gemini API quota limits are exceeded."""
    pass

# --- Helper Functions ---

def _call_gemini(prompt):
    """Runs the Gemini CLI with a given prompt, handling quota errors."""
    result = subprocess.run(
        ["gemini", "-p", prompt],
        capture_output=True,
        text=True,
        check=False # Do not raise CalledProcessError automatically
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
            print(f"No transcript processing entry found with id: {transcript_processing_id}")
            return

        progress_str = ""
        if current_index is not None and total_count is not None:
            progress_str = f" ({current_index}/{total_count})"
        
        print(f"Beginning {stage_name} for transcript {tp.id}{progress_str}...")

        # Execute the specific logic for this stage
        stage_logic_func(tp, db_session)

        # Update status and commit
        tp.status = success_status
        db_session.commit()
        print(f"{stage_name} complete for transcript: {tp.id}")

    except GeminiQuotaExceededError as e:
        print(f"!!! CRITICAL: Gemini API quota hit during {stage_name} for transcript {transcript_processing_id}. Stopping further LLM processing. Error: {e}")
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
        print(f"Error during {stage_name} for transcript {transcript_processing_id}: {e}")
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

    # Call the LLM to add paragraph breaks
    cleaned_text = _call_gemini(prompt)

    # Calculate cleaned text word count
    cleaned_word_count = len(cleaned_text.split())

    # Determine text to save based on word count loss
    text_to_save = cleaned_text
    word_loss_percentage = 0.0

    if initial_word_count > 0: # Avoid division by zero
        word_loss_percentage = (abs(initial_word_count - cleaned_word_count) / initial_word_count) * 100

    if word_loss_percentage > 2.0: # 2% threshold
        print(f"Warning: Secondary cleaning resulted in a {word_loss_percentage:.2f}% word count loss for transcript {tp.id}. Falling back to initial text.")
        text_to_save = initial_text
    else:
        print(f"Secondary cleaning word count change: {word_loss_percentage:.2f}% for transcript {tp.id}. Acceptable.")

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
    Logic for the metadata generation stage.
    """
    with open(tp.secondary_cleaning_path, 'r') as f:
        text_for_metadata = f.read()

    metadata = {}

    # 1. Get Title
    title = None
    match = re.search(r"The title of todays sermon is (.*?)[\.\n]", text_for_metadata, re.IGNORECASE)
    if match:
        title = match.group(1).strip()
    else:
        prompt = f"Please provide a single, concise, and suitable title for the following text. Do not include any introductory phrases or bullet points. Just the title itself.\n\n---\n\n{text_for_metadata}"
        title = _call_gemini(prompt)
    metadata['title'] = title

    # 2. Get other metadata fields
    fields_to_generate = {
        "thesis": "a concise thesis statement",
        "outline": "a structured outline",
        "summary": "a brief summary"
    }

    for field, description in fields_to_generate.items():
        print(f"Generating '{field}'...")
        prompt = f"Please generate {description} for the following text:\n\n---\n\n{text_for_metadata}"
        try:
            metadata[field] = _call_gemini(prompt)
        except RuntimeError as e:
            print(f"Error generating '{field}': {e}")
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
        print(f"Processing chunk {i+1}/{len(chunks)}...")
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
            print(f"Error processing chunk {i+1} for transcript {tp.id}: {e}")
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
        print(f"Missing paths for transcript processing id: {tp.id}")
        return

    # 1. Read existing metadata
    with open(tp.metadata_path, 'r') as f:
        try:
            metadata = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Could not parse JSON from {tp.metadata_path}. Starting with an empty metadata object.")
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
    print("\n--- Starting Transcript Post-Processing ---")
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
        print(f"Found {total_transcripts} transcripts to process through the pipeline.")

        for i, tp in enumerate(transcripts_to_process):
            if stop_processing[0]:
                print("Processing halted due to Gemini API quota or other error.")
                break
            
            print(f"\n--- Processing Transcript: {tp.id} ({i + 1}/{total_transcripts}) ---")

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
