import db
import re
from pathlib import Path
import subprocess

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
    tp = None  # Initialize tp to None
    try:
        tp = db_session.query(db.TranscriptProcessing).filter(db.TranscriptProcessing.id == transcript_processing_id).first()
        if not tp:
            print(f"No transcript processing entry found with id: {transcript_processing_id}")
            return

        # Execute the core logic for the stage
        stage_logic_func(db_session, tp)

        # If the logic function completes without error, update status and commit
        tp.status = success_status
        db_session.commit()
        print(f"{stage_name} complete for transcript: {tp.id}")

    except Exception as e:
        print(f"Error during {stage_name} for transcript {transcript_processing_id}: {e}")
        if db_session.is_active:
            db_session.rollback()
        # If tp was fetched, update its status to reflect the failure
        if tp:
            tp.status = f"{stage_name.lower().replace(' ', '_')}_failed"
            db_session.commit()
    finally:
        db_session.close()


# --- Core Logic for Each Stage ---

def _initial_cleaning_logic(db_session, tp):
    """Core logic for initial cleaning."""
    with open(tp.raw_transcript_path, 'r') as f:
        raw_text = f.read()
    cleaned_text = " ".join(raw_text.split())
    initial_cleaning_path = Path(tp.raw_transcript_path).with_suffix('.initial.txt')
    with open(initial_cleaning_path, 'w') as f:
        f.write(cleaned_text)
    tp.initial_cleaning_path = str(initial_cleaning_path)

def _secondary_cleaning_logic(db_session, tp):
    """Core logic for secondary cleaning."""
    with open(tp.initial_cleaning_path, 'r') as f:
        initial_text = f.read()
    
    prompt = f"You will be given a block of text. Your task is to insert the marker '[PB]' at every point where a natural paragraph break should occur. Do not add, remove, or change any of the original words. Simply return the original text with the '[PB]' markers inserted.\n\n{initial_text}"
    
    text_with_markers = _call_gemini(prompt)
    cleaned_text = text_with_markers.replace('[PB]', '\n\n')
    secondary_cleaning_path = Path(tp.raw_transcript_path).with_suffix('.secondary.txt')
    with open(secondary_cleaning_path, 'w') as f:
        f.write(cleaned_text)
    tp.secondary_cleaning_path = str(secondary_cleaning_path)

def _gen_metadata_logic(db_session, tp):
    """Core logic for metadata generation."""
    with open(tp.secondary_cleaning_path, 'r') as f:
        secondary_text = f.read()
    title = None
    match = re.search(r"The title of todays sermon is (.*?)[\\.\n]", secondary_text, re.IGNORECASE)
    
    if match:
        title = match.group(1).strip()
        prompt = f"Please generate the following metadata for the text below:\n\n1. A concise thesis statement.\n2. A structured outline.\n3. A brief summary.\n\n---\n\n{secondary_text}"
    else:
        prompt = f"Please generate the following metadata for the text below:\n\n1. A suitable title.\n2. A concise thesis statement.\n3. A structured outline.\n4. A brief summary.\n\n---\n\n{secondary_text}"
        
    generated_text = _call_gemini(prompt)
    
    if not title:
        title_match = re.search(r"1. Title: (.*?)[\\n]", generated_text, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            generated_text = re.sub(r"1. Title: .*?[\\n]", "", generated_text, count=1).lstrip()
            
    metadata_text = f"Title: {title or 'Untitled'}\n\n{generated_text}"
    metadata_path = Path(tp.raw_transcript_path).with_suffix('.meta.txt')
    with open(metadata_path, 'w') as f:
        f.write(metadata_text)
    tp.metadata_path = str(metadata_path)

def _final_pass_logic(db_session, tp):
    """Core logic for the final pass."""
    with open(tp.secondary_cleaning_path, 'r') as f:
        secondary_text = f.read()
    cleaned_text = secondary_text.lower()
    final_word_count = len(cleaned_text.split())
    final_pass_path = Path(tp.raw_transcript_path).with_suffix('.final.txt')
    with open(final_pass_path, 'w') as f:
        f.write(cleaned_text)
    tp.final_pass_path = str(final_pass_path)
    tp.final_word_count = final_word_count

def _llm_book_cleanup_logic(db_session, tp):
    """Core logic for the LLM book cleanup."""
    with open(tp.final_pass_path, 'r') as f:
        text_to_clean = f.read()
    # Chunking logic
    paragraphs = text_to_clean.split('\n\n')
    chunks, current_chunk = [], ""
    for p in paragraphs:
        if len(current_chunk.split()) + len(p.split()) < 1000:
            current_chunk += p + "\n\n"
        else:
            chunks.append(current_chunk)
            current_chunk = p + "\n\n"
    if current_chunk: chunks.append(current_chunk)
    # LLM processing
    cleaned_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}...")
        
        prompt_disfluency = f"Please remove filler words like 'um', 'ah', and 'you know' from the following text:\n\n{chunk}"
        cleaned_chunk = _call_gemini(prompt_disfluency)

        prompt_grammar = f"Please correct any grammar and spelling errors in the following text:\n\n{cleaned_chunk}"
        cleaned_chunk = _call_gemini(prompt_grammar)

        prompt_style = f"Please improve the flow, clarity, and sentence structure of the following text to make it suitable for a book:\n\n{cleaned_chunk}"
        cleaned_chunk = _call_gemini(prompt_style)
        
        cleaned_chunks.append(cleaned_chunk)
        
    final_text = "\n\n".join(cleaned_chunks)
    book_ready_path = Path(tp.raw_transcript_path).with_suffix('.book.txt')
    with open(book_ready_path, 'w') as f:
        f.write(final_text)
    tp.book_ready_path = str(book_ready_path)

def _update_metadata_file_logic(db_session, tp):
    """Core logic for updating the metadata file."""
    if not tp.book_ready_path or not tp.metadata_path:
        print(f"Missing paths for transcript processing id: {tp.id}")
        return
    with open(tp.book_ready_path, 'r') as f:
        book_text = f.read()
    word_count = len(book_text.split())
    duration_str = _get_video_duration_str(db_session, tp.video_id)
    with open(tp.metadata_path, 'a') as f:
        f.write(f"\n\nFinal Word Count: {word_count}")
        f.write(f"\nTrimmed Video Duration: {duration_str}")

# --- Public-Facing Functions for Each Stage ---

def initial_cleaning(transcript_processing_id):
    _execute_processing_stage(transcript_processing_id, _initial_cleaning_logic, "initial_cleaning_complete", "Initial Cleaning")

def secondary_cleaning(transcript_processing_id):
    _execute_processing_stage(transcript_processing_id, _secondary_cleaning_logic, "secondary_cleaning_complete", "Secondary Cleaning")

def gen_metadata(transcript_processing_id):
    _execute_processing_stage(transcript_processing_id, _gen_metadata_logic, "metadata_generation_complete", "Metadata Generation")

def final_pass(transcript_processing_id):
    _execute_processing_stage(transcript_processing_id, _final_pass_logic, "final_pass_complete", "Final Pass")

def llm_book_cleanup(transcript_processing_id):
    _execute_processing_stage(transcript_processing_id, _llm_book_cleanup_logic, "book_ready_complete", "LLM Book Cleanup")

def update_metadata_file(transcript_processing_id):
    _execute_processing_stage(transcript_processing_id, _update_metadata_file_logic, "metadata_updated", "Update Metadata File")


# --- Main Orchestration ---

def post_process_transcripts():
    """
    Main function to orchestrate the post-processing of transcripts
    by advancing them through a state machine.
    """
    db_session = db.SessionLocal()
    try:
        # State machine definition
        processing_stages = {
            "raw_transcript_received": initial_cleaning,
            "initial_cleaning_complete": secondary_cleaning,
            "secondary_cleaning_complete": gen_metadata,
            "metadata_generation_complete": final_pass,
        }

        # Find all transcripts that are in a processable state
        transcripts_to_process = db_session.query(db.TranscriptProcessing).filter(
            db.TranscriptProcessing.status.in_(processing_stages.keys())
        ).all()

        if not transcripts_to_process:
            print("No transcripts to process.")
            return

        print(f"Found {len(transcripts_to_process)} transcripts to process.")

        # Loop through transcripts and process them one stage at a time
        for tp in transcripts_to_process:
            current_status = tp.status
            if current_status in processing_stages:
                stage_function = processing_stages[current_status]
                print(f"--- Running {stage_function.__name__} for transcript {tp.id} (Status: {current_status}) ---")
                # This function call will handle the entire stage, including DB updates
                stage_function(tp.id)

    finally:
        db_session.close()