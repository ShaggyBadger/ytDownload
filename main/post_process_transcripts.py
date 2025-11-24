import db
import math, re, json
from pathlib import Path
import subprocess
from sqlalchemy import or_
from utils import get_video_paths # <--- Added import

# --- Helper Functions ---

def _call_gemini(prompt):
    """Runs the Gemini CLI with a given prompt."""
    result = subprocess.run(
        ["gemini", "-p", prompt],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Gemini CLI error: {result.stderr.strip()}")
    return result.stdout.strip()

def _get_video_duration_str(db_session, video_id):
    """Fetches and formats the trimmed duration of a video."""
    video = db_session.query(db.Video).filter(db.Video.id == video_id).first()
    if video and video.end_time and video.start_time:
        duration = video.end_time - video.start_time
        return f"{duration // 60} minutes, {duration % 60} seconds"
    return "Unknown"

# --- Centralized Processing Logic ---

def _execute_processing_stage(transcript_processing_id, stage_logic_func, success_status, stage_name):
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

        # Execute the specific logic for this stage
        stage_logic_func(tp, db_session)

        # Update status and commit
        tp.status = success_status
        db_session.commit()
        print(f"{stage_name} complete for transcript: {tp.id}")

    except Exception as e:
        print(f"Error during {stage_name} for transcript {transcript_processing_id}: {e}")
        if db_session.is_active:
            db_session.rollback()
        if tp:
            tp.status = f"{stage_name.lower().replace(' ', '_')}_failed"
            db_session.commit()
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

def initial_cleaning(transcript_processing_id):
    """
    Public-facing function for the initial cleaning stage.
    """
    _execute_processing_stage(
        transcript_processing_id,
        _initial_cleaning_logic,
        "initial_cleaning_complete",
        "Initial Cleaning"
    )

def _secondary_cleaning_logic(tp, db_session):
    """
    Logic for the secondary cleaning stage.
    """
    # Read the initially cleaned transcript
    with open(tp.initial_cleaning_path, 'r') as f:
        initial_text = f.read()

    # Create a prompt for the LLM
    prompt = f"Please add paragraph breaks to the following text:\n\n{initial_text}"

    # Call the LLM to add paragraph breaks
    cleaned_text = _call_gemini(prompt)

    # Write the cleaned text to a new file
    secondary_cleaning_path = Path(tp.raw_transcript_path).with_suffix('.secondary.txt')
    with open(secondary_cleaning_path, 'w') as f:
        f.write(cleaned_text)

    # Update the database
    tp.secondary_cleaning_path = str(secondary_cleaning_path)

def secondary_cleaning(transcript_processing_id):
    """
    Public-facing function for the secondary cleaning stage.
    """
    _execute_processing_stage(
        transcript_processing_id,
        _secondary_cleaning_logic,
        "secondary_cleaning_complete",
        "Secondary Cleaning"
    )


def _gen_metadata_logic(tp, db_session):
    """
    Logic for the metadata generation stage.
    """
    with open(tp.secondary_cleaning_path, 'r') as f:
        secondary_text = f.read()

    title = None
    # Try to find title in text
    match = re.search(r"The title of todays sermon is (.*?)[\.\n]", secondary_text, re.IGNORECASE)
    if match:
        title = match.group(1).strip()
        prompt = f"Please generate the following metadata for the text below:\n\n1. A concise thesis statement.\n2. A structured outline.\n3. A brief summary.\n\n---\n\n{secondary_text}"
    else:
        prompt = f"Please generate the following metadata for the text below:\n\n1. A suitable title.\n2. A concise thesis statement.\n3. A structured outline.\n4. A brief summary.\n\n---\n\n{secondary_text}"

    generated_text = _call_gemini(prompt)

    if not title:
        # Extract title from generated text
        title_match = re.search(r"1. Title: (.*?)[\n]", generated_text, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            # Remove title from generated text
            generated_text = re.sub(r"1. Title: .*?[\n]", "", generated_text, count=1)

    metadata_text = f"Title: {title}\n\n{generated_text}"

    metadata_path = Path(tp.raw_transcript_path).with_suffix('.meta.txt')
    with open(metadata_path, 'w') as f:
        f.write(metadata_text)

    tp.metadata_path = str(metadata_path)

def gen_metadata(transcript_processing_id):
    """
    Public-facing function for the metadata generation stage.
    """
    _execute_processing_stage(
        transcript_processing_id,
        _gen_metadata_logic,
        "metadata_generation_complete",
        "Metadata Generation"
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
    # Read the final pass transcript
    with open(tp.final_pass_path, 'r') as f:
        final_pass_text = f.read()

    # Perform python_scrub (example: remove all instances of the word "the")
    cleaned_text = final_pass_text.replace(" the ", " ")

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

    # Calculate word count
    with open(tp.book_ready_path, 'r') as f:
        book_text = f.read()
    word_count = len(book_text.split())

    # Get video duration
    duration_str = _get_video_duration_str(db_session, tp.video_id)

    # Append to metadata file
    with open(tp.metadata_path, 'a') as f:
        f.write(f"\n\nFinal Word Count: {word_count}")
        f.write(f"\nTrimmed Video Duration: {duration_str}")

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

# --- Main Orchestration ---

def post_process_transcripts():
    """
    Main function to orchestrate the post-processing of transcripts
    by advancing them through a state machine.
    """
    print("\n--- Starting Transcript Post-Processing ---")
    db_session = db.SessionLocal()
    try:
        # Find all transcripts that need processing
        transcripts_to_process = db_session.query(db.TranscriptProcessing).filter(db.TranscriptProcessing.status == "raw_transcript_received").all()
        for tp in transcripts_to_process:
            initial_cleaning(tp.id)

        transcripts_to_process = db_session.query(db.TranscriptProcessing).filter(db.TranscriptProcessing.status == "initial_cleaning_complete").all()
        for tp in transcripts_to_process:
            secondary_cleaning(tp.id)

        transcripts_to_process = db_session.query(db.TranscriptProcessing).filter(db.TranscriptProcessing.status == "secondary_cleaning_complete").all()
        for tp in transcripts_to_process:
            gen_metadata(tp.id)

        transcripts_to_process = db_session.query(db.TranscriptProcessing).filter(db.TranscriptProcessing.status == "metadata_generation_complete").all()
        for tp in transcripts_to_process:
            final_pass(tp.id)

        transcripts_to_process = db_session.query(db.TranscriptProcessing).filter(db.TranscriptProcessing.status == "final_pass_complete").all()
        for tp in transcripts_to_process:
            python_scrub(tp.id)
            break
            
    finally:
        db_session.close()
