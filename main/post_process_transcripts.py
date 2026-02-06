from tkinter import E
from joshlib.ollama import OllamaClient, OllamaProcessingError
from joshlib.gemini import GeminiClient
import db
import math, re, json, os
from pathlib import Path
import subprocess
from sqlalchemy import or_
import utils
from logger import setup_logger
import time

logger = setup_logger(__name__)
ollama_processor = OllamaClient()


# --- Custom Exceptions ---
class GeminiQuotaExceededError(Exception):
    """Custom exception for when Gemini API quota limits are exceeded."""

    pass


# --- Helper Functions ---


def _call_gemini(prompt, retries=3, delay=5):
    """
    Calls the Gemini CLI with the given prompt, with retry logic.
    """
    logger.debug(
        f"Attempting to call Gemini CLI with prompt of length {len(prompt)} characters."
    )
    for attempt in range(retries):
        logger.info(f"Gemini call attempt {attempt + 1}/{retries}")
        try:
            # Note: The path to the gemini executable should be in the system's PATH
            process = subprocess.run(
                ["gemini"], input=prompt, capture_output=True, text=True, check=True
            )

            # Check for quota error message in stderr, even if process exits successfully
            if "quota" in process.stderr.lower():
                logger.warning(
                    f"Gemini API quota exceeded on attempt {attempt + 1}. STDERR: {process.stderr}"
                )
                raise GeminiQuotaExceededError(
                    f"Gemini API quota exceeded: {process.stderr}"
                )

            logger.debug(
                f"Gemini call successful on attempt {attempt + 1}. STDOUT: {process.stdout[:100]}..."
            )
            return process.stdout.strip()

        except FileNotFoundError:
            logger.error(
                "CRITICAL: 'gemini' command not found. Make sure the Gemini CLI is installed and in your system's PATH."
            )
            raise RuntimeError("Gemini CLI not found.")
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Gemini CLI call failed on attempt {attempt + 1} with exit code {e.returncode}:"
            )
            logger.error(f"STDOUT: {e.stdout}")
            logger.error(f"STDERR: {e.stderr}")
            if "quota" in e.stderr.lower():
                logger.critical(
                    f"Gemini API quota exceeded. Raising GeminiQuotaExceededError. STDERR: {e.stderr}"
                )
                raise GeminiQuotaExceededError(f"Gemini API quota exceeded: {e.stderr}")
            if attempt < retries - 1:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error(f"Gemini CLI call failed after {retries} attempts.")
                raise RuntimeError(f"Gemini CLI call failed after {retries} attempts.")
        except GeminiQuotaExceededError as e:
            # Re-raise the specific quota error to be handled by the calling function
            logger.critical(
                "Caught GeminiQuotaExceededError. Re-raising to halt processing."
            )
            raise e
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during Gemini CLI call on attempt {attempt + 1}: {e}",
                exc_info=True,
            )
            if attempt < retries - 1:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error(f"An unexpected error occurred after {retries} attempts.")
                raise RuntimeError(f"An unexpected error occurred: {e}")


# --- Centralized Processing Logic ---


def _execute_processing_stage(
    transcript_processing_id,
    stage_logic_func,
    success_status,
    stage_name,
    current_index=None,
    total_count=None,
    stop_processing_flag=None,
):
    """
    A helper function to manage the boilerplate of a processing stage.
    - Opens a DB session.
    - Fetches the transcript processing object.
    - Executes the provided stage logic.
    - Handles success, errors, and session closing.
    """
    logger.debug(
        f"Executing stage '{stage_name}' for transcript_processing_id: {transcript_processing_id}"
    )
    db_session = db.SessionLocal()
    tp = None
    try:
        tp = (
            db_session.query(db.TranscriptProcessing)
            .filter(db.TranscriptProcessing.id == transcript_processing_id)
            .first()
        )
        if not tp:
            logger.error(
                f"No transcript processing entry found with id: {transcript_processing_id}. Stage '{stage_name}' aborted."
            )
            return

        progress_str = ""
        if current_index is not None and total_count is not None:
            progress_str = f" ({current_index}/{total_count})"

        logger.info(f"Beginning {stage_name} for transcript {tp.id}{progress_str}...")
        logger.debug(f"Initial status for transcript {tp.id}: {tp.status}")

        # Execute the specific logic for this stage
        stage_logic_func(tp, db_session)

        # Update status and commit
        logger.debug(f"Updating status for transcript {tp.id} to '{success_status}'")
        tp.status = success_status
        db_session.commit()
        logger.info(f"Successfully completed {stage_name} for transcript: {tp.id}")

    except (GeminiQuotaExceededError, OllamaProcessingError) as e:
        model_name = "Gemini" if isinstance(e, GeminiQuotaExceededError) else "Ollama"
        new_status = (
            f"{stage_name.lower().replace(' ', '_')}_{model_name.lower()}_failed"
        )
        logger.critical(
            f"!!! CRITICAL: {model_name} API processing issue during {stage_name} for transcript {transcript_processing_id}. New status: '{new_status}'. Stopping further LLM processing. Error: {e}",
            exc_info=True,
        )
        if stop_processing_flag is not None:
            logger.debug("Setting stop_processing_flag to True.")
            stop_processing_flag[0] = True
        if db_session.is_active:
            db_session.rollback()
            logger.debug("Database session rolled back.")
        if tp:
            logger.debug(f"Updating status for transcript {tp.id} to '{new_status}'")
            tp.status = new_status
            db_session.commit()
            logger.info(
                f"Status updated for transcript {tp.id} after {model_name} API failure."
            )
        # Re-raise to stop current transcript's processing
        raise RuntimeError(
            f"Processing halted due to {model_name} API processing issue."
        ) from e
    except Exception as e:
        new_status = f"{stage_name.lower().replace(' ', '_')}_failed"
        logger.error(
            f"An unexpected error occurred during {stage_name} for transcript {transcript_processing_id}. New status: '{new_status}'. Error: {e}",
            exc_info=True,
        )
        if db_session.is_active:
            db_session.rollback()
            logger.debug("Database session rolled back.")
        if tp:
            logger.debug(f"Updating status for transcript {tp.id} to '{new_status}'")
            tp.status = new_status
            db_session.commit()
            logger.info(
                f"Status updated for transcript {tp.id} after unexpected error."
            )
        # Re-raise to stop current transcript's processing
        raise RuntimeError(f"Processing halted due to unexpected error.") from e
    finally:
        logger.debug(
            f"Closing database session for stage '{stage_name}', transcript {transcript_processing_id}."
        )
        db_session.close()


def _initial_cleaning_logic(tp, db_session):
    """
    Logic for the initial cleaning stage.
    """
    logger.debug(f"Entering _initial_cleaning_logic for transcript {tp.id}")
    try:
        # Read the raw transcript
        logger.debug(f"Reading raw transcript from: {tp.raw_transcript_path}")
        with open(tp.raw_transcript_path, "r") as f:
            raw_text = f.read()
        logger.debug(
            f"Successfully read {len(raw_text)} characters from raw transcript."
        )

        # Perform initial cleaning (example: remove extra whitespace)
        logger.debug("Performing initial cleaning (removing extra whitespace).")
        cleaned_text = " ".join(raw_text.split())
        logger.debug(f"Cleaned text length: {len(cleaned_text)} characters.")

        # Write the cleaned text to a new file
        initial_cleaning_path = Path(tp.raw_transcript_path).with_suffix(".initial.txt")
        logger.debug(f"Writing cleaned text to: {initial_cleaning_path}")
        with open(initial_cleaning_path, "w") as f:
            f.write(cleaned_text)
        logger.debug("Successfully wrote cleaned text.")

        # Update the database
        logger.debug(
            f"Updating database with initial_cleaning_path: {initial_cleaning_path}"
        )
        tp.initial_cleaning_path = str(initial_cleaning_path)
        logger.debug(f"Exiting _initial_cleaning_logic for transcript {tp.id}")
    except FileNotFoundError as e:
        logger.error(
            f"File not found during initial cleaning for transcript {tp.id}: {e}",
            exc_info=True,
        )
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred in _initial_cleaning_logic for transcript {tp.id}: {e}",
            exc_info=True,
        )
        raise


def initial_cleaning(
    transcript_processing_id,
    current_index=None,
    total_count=None,
    stop_processing_flag=None,
):
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
        stop_processing_flag=stop_processing_flag,
    )


def _secondary_cleaning_logic(tp, db_session):
    """
    Logic for the secondary cleaning stage.
    """
    # Read the initially cleaned transcript
    with open(tp.initial_cleaning_path, "r") as f:
        initial_text = f.read()

    # Calculate initial word count
    initial_word_count = len(initial_text.split())

    # Create a prompt for the LLM
    BASE_DIR = Path(__file__).resolve().parent
    PROMPTS_DIR = BASE_DIR / "prompts"

    prompt_template_path = PROMPTS_DIR / "format-paragraph.txt"
    prompt_template = prompt_template_path.read_text()
    prompt = prompt_template.format(SERMON_TEXT=initial_text)

    max_retries = 3

    for attempt in range(max_retries):
        logger.info(
            f"Secondary cleaning attempt {attempt + 1}/{max_retries} for transcript {tp.id}..."
        )

        # Call the LLM to add paragraph breaks
        cleaned_text = _call_gemini(prompt)

        # Calculate cleaned text word count
        cleaned_word_count = len(cleaned_text.split())

        # Determine word count loss
        word_loss_percentage = 0.0
        if initial_word_count > 0:  # Avoid division by zero
            word_loss_percentage = (
                abs(initial_word_count - cleaned_word_count) / initial_word_count
            ) * 100

        if word_loss_percentage <= 2.0:  # 2% threshold
            logger.info(
                f"Secondary cleaning word count change: {word_loss_percentage:.2f}%. Acceptable."
            )

            # Write the successful text to a new file
            secondary_cleaning_path = Path(tp.raw_transcript_path).with_suffix(
                ".secondary.txt"
            )
            with open(secondary_cleaning_path, "w") as f:
                f.write(cleaned_text)

            # Update the database
            tp.secondary_cleaning_path = str(secondary_cleaning_path)
            return  # Success, exit the function

        else:
            logger.warning(
                f"Warning: Attempt {attempt + 1} resulted in a {word_loss_percentage:.2f}% word count loss. Retrying..."
            )

    # This part is only reached if all retries fail
    logger.error(
        f"All {max_retries} secondary cleaning attempts resulted in high word count loss for transcript {tp.id}. Halting processing for this transcript."
    )
    raise RuntimeError(
        f"Failed to get acceptable paragraphing from Gemini after {max_retries} attempts."
    )


def secondary_cleaning(
    transcript_processing_id,
    current_index=None,
    total_count=None,
    stop_processing_flag=None,
):
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
        stop_processing_flag=stop_processing_flag,
    )


def _gen_metadata_logic(tp, db_session):
    """
    Logic for the metadata generation stage, processing fields sequentially.
    """
    BASE_DIR = Path(__file__).resolve().parent
    PROMPTS_DIR = BASE_DIR / "prompts"

    # Defensive check for the input file
    if not tp.secondary_cleaning_path or not Path(tp.secondary_cleaning_path).is_file():
        error_msg = f"Input file for metadata generation not found or is invalid for transcript {tp.id}. Expected path: {tp.secondary_cleaning_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    with open(tp.secondary_cleaning_path, "r") as f:
        text_for_metadata = f.read()

    metadata = {}

    # 1. Get Title (sequentially, as it's a single call with custom logic)
    logger.info("Generating 'title'...")
    # load prompt templates
    title_prompt_path = PROMPTS_DIR / "generate-title.txt"
    prompt_template = title_prompt_path.read_text()
    prompt = prompt_template.format(SERMON_TEXT=text_for_metadata)
    logger.info(f"Submitting prompt for 'title'")
    title = _call_gemini(prompt)
    logger.info(f"Title generation complete")
    metadata["title"] = title

    # 2. Get other metadata fields sequentially
    thesis_prompt_path = PROMPTS_DIR / "generate-thesis.txt"
    prompt_template = thesis_prompt_path.read_text()
    prompt = prompt_template.format(SERMON_TEXT=text_for_metadata)
    logger.info(f"Submitting prompt for 'thesis'")
    thesis = _call_gemini(prompt)
    metadata["thesis"] = thesis

    summary_prompt_path = PROMPTS_DIR / "generate-summary.txt"
    prompt_template = summary_prompt_path.read_text()
    prompt = prompt_template.format(SERMON_TEXT=text_for_metadata)
    logger.info(f"Submitting prompt for 'summary'")
    summary = _call_gemini(prompt)
    metadata["summary"] = summary

    outline_prompt_path = PROMPTS_DIR / "generate-outline.txt"
    prompt_template = outline_prompt_path.read_text()
    prompt = prompt_template.format(SERMON_TEXT=text_for_metadata)
    logger.info(f"Submitting prompt for 'outline'")
    outline = _call_gemini(prompt)
    metadata["outline"] = outline

    tone_propmt_path = PROMPTS_DIR / "generate-tone.txt"
    prompt_template = tone_propmt_path.read_text()
    prompt = prompt_template.format(SERMON_TEXT=text_for_metadata)
    logger.info(f"Submitting prompt for 'tone'")
    tone = _call_gemini(prompt)
    metadata["tone"] = tone

    references_prompt_path = PROMPTS_DIR / "generate-references.txt"
    prompt_template = references_prompt_path.read_text()
    prompt = prompt_template.format(SERMON_TEXT=text_for_metadata)
    logger.info(f"Submitting prompt for 'references'")
    references = _call_gemini(prompt)
    metadata["references"] = references

    # 3. Write to file as JSON
    metadata_path = Path(tp.raw_transcript_path).with_suffix(".meta.txt")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)

    tp.metadata_path = str(metadata_path)


def gen_metadata(
    transcript_processing_id,
    current_index=None,
    total_count=None,
    stop_processing_flag=None,
):
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
        stop_processing_flag=stop_processing_flag,
    )


def _final_pass_logic(tp, db_session):
    """
    Logic for the final pass stage.
    """
    logger.debug(f"Entering _final_pass_logic for transcript {tp.id}")
    try:
        # Read the secondarily cleaned transcript
        logger.debug(
            f"Reading secondary cleaned transcript from: {tp.secondary_cleaning_path}"
        )
        with open(tp.secondary_cleaning_path, "r") as f:
            secondary_text = f.read()
        logger.debug(
            f"Successfully read {len(secondary_text)} characters from secondary cleaned transcript."
        )

        # Perform final pass (example: convert to lowercase)
        logger.debug("Performing final pass (converting to lowercase).")
        cleaned_text = secondary_text.lower()
        logger.debug(f"Cleaned text length: {len(cleaned_text)} characters.")

        # Calculate the final word count
        final_word_count = len(cleaned_text.split())
        logger.info(f"Final word count for transcript {tp.id}: {final_word_count}")

        # Write the cleaned text to a new file
        final_pass_path = Path(tp.raw_transcript_path).with_suffix(".final.txt")
        logger.debug(f"Writing final pass text to: {final_pass_path}")
        with open(final_pass_path, "w") as f:
            f.write(cleaned_text)
        logger.debug("Successfully wrote final pass text.")

        # Update the database
        logger.debug(
            f"Updating database with final_pass_path: {final_pass_path} and final_word_count: {final_word_count}"
        )
        tp.final_pass_path = str(final_pass_path)
        tp.final_word_count = final_word_count
        logger.debug(f"Exiting _final_pass_logic for transcript {tp.id}")
    except FileNotFoundError as e:
        logger.error(
            f"File not found during final pass for transcript {tp.id}: {e}",
            exc_info=True,
        )
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred in _final_pass_logic for transcript {tp.id}: {e}",
            exc_info=True,
        )
        raise


def final_pass(transcript_processing_id):
    """
    Public-facing function for the final pass stage.
    """
    _execute_processing_stage(
        transcript_processing_id, _final_pass_logic, "final_pass_complete", "Final Pass"
    )


def _python_scrub_logic(tp, db_session):
    """
    Logic for the python_scrub stage.
    """
    logger.debug(f"Entering _python_scrub_logic for transcript {tp.id}")
    try:
        # Read the initial cleaning transcript
        logger.debug(
            f"Reading initial cleaned transcript from: {tp.initial_cleaning_path}"
        )
        with open(tp.initial_cleaning_path, "r") as f:
            initial_cleaning_text = f.read()
        logger.debug(
            f"Successfully read {len(initial_cleaning_text)} characters from initial cleaned transcript."
        )

        # Perform python_scrub (example: remove all instances of the word "the")
        logger.debug("Performing python scrub (removing all instances of ' the ').")
        cleaned_text = initial_cleaning_text.replace(" the ", " ")
        logger.debug(f"Cleaned text length: {len(cleaned_text)} characters.")

        # Write the cleaned text to a new file
        python_scrub_path = Path(tp.raw_transcript_path).with_suffix(".scrubbed.txt")
        logger.debug(f"Writing python scrubbed text to: {python_scrub_path}")
        with open(python_scrub_path, "w") as f:
            f.write(cleaned_text)
        logger.debug("Successfully wrote python scrubbed text.")

        # Update the database
        logger.debug(f"Updating database with python_scrub_path: {python_scrub_path}")
        tp.python_scrub_path = str(python_scrub_path)
        logger.debug(f"Exiting _python_scrub_logic for transcript {tp.id}")
    except FileNotFoundError as e:
        logger.error(
            f"File not found during python scrub for transcript {tp.id}: {e}",
            exc_info=True,
        )
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred in _python_scrub_logic for transcript {tp.id}: {e}",
            exc_info=True,
        )
        raise


def python_scrub(transcript_processing_id):
    """
    Public-facing function for the python_scrub stage.
    """
    _execute_processing_stage(
        transcript_processing_id,
        _python_scrub_logic,
        "python_scrub_complete",
        "Python Scrub",
    )


def _llm_book_cleanup_logic(tp, db_session):
    """
    Logic for the LLM book cleanup stage.
    """
    logger.debug(f"Entering _llm_book_cleanup_logic for transcript {tp.id}")
    try:
        logger.debug(f"Reading python scrubbed transcript from: {tp.python_scrub_path}")
        with open(tp.python_scrub_path, "r") as f:
            text_to_clean = f.read()
        logger.debug(
            f"Successfully read {len(text_to_clean)} characters from python scrubbed transcript."
        )

        # 1. Chunk the text
        paragraphs = text_to_clean.split("\n\n")
        chunks = []
        current_chunk = ""
        for p in paragraphs:
            if len(current_chunk.split()) + len(p.split()) < 1000:
                current_chunk += p + "\n\n"
            else:
                chunks.append(current_chunk)
                current_chunk = p + "\n\n"
        chunks.append(current_chunk)
        logger.info(
            f"Text for transcript {tp.id} has been split into {len(chunks)} chunks."
        )

        cleaned_chunks = []
        for i, chunk in enumerate(chunks):
            logger.info(
                f"Processing chunk {i+1}/{len(chunks)} for transcript {tp.id}..."
            )
            try:
                # 2a. Disfluency Removal
                logger.debug(f"Chunk {i+1}: Submitting for disfluency removal.")
                prompt_disfluency = f"Please remove filler words like 'um', 'ah', and 'you know' from the following text:\n\n{chunk}"
                cleaned_chunk = ollama_processor.submit_prompt(prompt_disfluency)
                logger.debug(f"Chunk {i+1}: Disfluency removal complete.")

                # 2b. Grammar Correction
                logger.debug(f"Chunk {i+1}: Submitting for grammar correction.")
                prompt_grammar = f"Please correct any grammar and spelling errors in the following text:\n\n{cleaned_chunk}"
                cleaned_chunk = ollama_processor.submit_prompt(prompt_grammar)
                logger.debug(f"Chunk {i+1}: Grammar correction complete.")

                # 2c. Stylistic Enhancement
                logger.debug(f"Chunk {i+1}: Submitting for stylistic enhancement.")
                prompt_style = f"Please improve the flow, clarity, and sentence structure of the following text to make it suitable for a book:\n\n{cleaned_chunk}"
                cleaned_chunk = ollama_processor.submit_prompt(prompt_style)
                logger.debug(f"Chunk {i+1}: Stylistic enhancement complete.")

                cleaned_chunks.append(cleaned_chunk)
                logger.info(
                    f"Successfully processed chunk {i+1}/{len(chunks)} for transcript {tp.id}."
                )
            except RuntimeError as e:
                logger.error(
                    f"Error processing chunk {i+1} for transcript {tp.id}: {e}",
                    exc_info=True,
                )
                # Depending on desired behavior, you might want to append the original chunk or skip it
                # For now, we re-raise to let the main error handler catch it.
                raise e

        # 3. Reassemble the sermon
        logger.debug(
            f"Reassembling {len(cleaned_chunks)} cleaned chunks for transcript {tp.id}."
        )
        final_text = "\n\n".join(cleaned_chunks)
        logger.info(
            f"Final text for transcript {tp.id} reassembled, length: {len(final_text)} characters."
        )

        # 4. Save and Update
        book_ready_path = Path(tp.raw_transcript_path).with_suffix(".book.txt")
        logger.debug(f"Writing book-ready text to: {book_ready_path}")
        with open(book_ready_path, "w") as f:
            f.write(final_text)
        logger.debug("Successfully wrote book-ready text.")

        logger.debug(f"Updating database with book_ready_path: {book_ready_path}")
        tp.book_ready_path = str(book_ready_path)
        logger.debug(f"Exiting _llm_book_cleanup_logic for transcript {tp.id}")
    except FileNotFoundError as e:
        logger.error(
            f"File not found during LLM book cleanup for transcript {tp.id}: {e}",
            exc_info=True,
        )
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred in _llm_book_cleanup_logic for transcript {tp.id}: {e}",
            exc_info=True,
        )
        raise


def llm_book_cleanup(transcript_processing_id):
    """
    Public-facing function for the LLM book cleanup stage.
    """
    _execute_processing_stage(
        transcript_processing_id,
        _llm_book_cleanup_logic,
        "book_ready_complete",
        "LLM Book Cleanup",
    )


def _update_metadata_file_logic(tp, db_session):
    """
    Logic for the update metadata file stage.
    """
    logger.debug(f"Entering _update_metadata_file_logic for transcript {tp.id}")
    try:
        if not tp.book_ready_path or not tp.metadata_path:
            logger.error(
                f"Missing book_ready_path or metadata_path for transcript {tp.id}. Aborting metadata update."
            )
            raise ValueError("Missing required paths for metadata update.")

        # 1. Read existing metadata
        logger.debug(f"Reading existing metadata from: {tp.metadata_path}")
        with open(tp.metadata_path, "r") as f:
            try:
                metadata = json.load(f)
                logger.debug("Successfully loaded existing metadata.")
            except json.JSONDecodeError:
                logger.warning(
                    f"Could not parse JSON from {tp.metadata_path}. Starting with an empty metadata object."
                )
                metadata = {}

        # 2. Calculate word count
        logger.debug(
            f"Reading book-ready text from: {tp.book_ready_path} to calculate final word count."
        )
        with open(tp.book_ready_path, "r") as f:
            book_text = f.read()
        word_count = len(book_text.split())
        logger.info(f"Calculated final word count for transcript {tp.id}: {word_count}")

        # 3. Get video duration
        logger.debug(f"Fetching video duration for video_id: {tp.video_id}")
        duration_str = utils._get_video_duration_str(db_session, tp.video_id)
        if duration_str:
            logger.info(
                f"Retrieved video duration for transcript {tp.id}: {duration_str}"
            )
        else:
            logger.warning(f"Could not retrieve video duration for transcript {tp.id}.")

        # 4. Add new data
        logger.debug(
            f"Updating metadata object for transcript {tp.id} with final_word_count and trimmed_video_duration."
        )
        metadata["final_word_count"] = word_count
        metadata["trimmed_video_duration"] = duration_str

        # 5. Write updated metadata back to file
        logger.debug(f"Writing updated metadata to: {tp.metadata_path}")
        with open(tp.metadata_path, "w") as f:
            json.dump(metadata, f, indent=4)
        logger.info(f"Successfully wrote updated metadata for transcript {tp.id}.")
        logger.debug(f"Exiting _update_metadata_file_logic for transcript {tp.id}")
    except FileNotFoundError as e:
        logger.error(
            f"File not found during metadata update for transcript {tp.id}: {e}",
            exc_info=True,
        )
        raise
    except Exception as e:
        logger.error(
            f"An unexpected error occurred in _update_metadata_file_logic for transcript {tp.id}: {e}",
            exc_info=True,
        )
        raise


def update_metadata_file(transcript_processing_id):
    """
    Public-facing function for the update metadata file stage.
    """
    _execute_processing_stage(
        transcript_processing_id,
        _update_metadata_file_logic,
        "metadata_updated",
        "Update Metadata File",
    )


import sermon_exporter  # Add this import
import argparse  # Add this import

# ... existing code ...


def _export_sermon_file_logic(tp, db_session):
    """
    Logic for the sermon export file generation stage.
    """
    logger.debug(f"Entering _export_sermon_file_logic for transcript {tp.id}")
    try:
        # Simply call the new function from sermon_exporter
        logger.info(
            f"Delegating sermon export for transcript {tp.id} to sermon_exporter.export_single_sermon."
        )
        sermon_exporter.export_single_sermon(tp.id)
        logger.debug(f"Sermon export call for transcript {tp.id} finished.")
        # The sermon_exporter function is expected to print its own success/error messages
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during sermon export for transcript {tp.id}: {e}",
            exc_info=True,
        )
        raise
    logger.debug(f"Exiting _export_sermon_file_logic for transcript {tp.id}")


def export_sermon_file(
    transcript_processing_id,
    current_index=None,
    total_count=None,
    stop_processing_flag=None,
):
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
        stop_processing_flag=stop_processing_flag,
    )


def reset_transcript_status(transcript_id, db_session):
    """
    Resets the status of a transcript and its associated video in the database.
    This function does NOT delete any files.
    """
    logger.info(
        f"--- Attempting to reset status for transcript ID: {transcript_id} ---"
    )
    try:
        transcript = (
            db_session.query(db.TranscriptProcessing)
            .filter(db.TranscriptProcessing.id == transcript_id)
            .first()
        )
        if not transcript:
            logger.error(
                f"No transcript processing entry found with id: {transcript_id}. Reset failed."
            )
            return

        logger.debug(
            f"Found transcript to reset: {transcript.id}, current status: {transcript.status}"
        )

        # Reset status on TranscriptProcessing
        logger.debug("Resetting TranscriptProcessing fields to initial state.")
        transcript.book_ready_path = None
        transcript.final_pass_path = None
        transcript.metadata_path = None
        transcript.initial_cleaning_path = None
        transcript.secondary_cleaning_path = None
        transcript.python_scrub_path = None
        transcript.status = "raw_transcript_received"

        # Also reset status on the Video table
        video = (
            db_session.query(db.Video)
            .filter(db.Video.id == transcript.video_id)
            .first()
        )
        if video:
            logger.info(f"Resetting video status for associated video ID: {video.id}")
            logger.debug(
                f"Original video statuses: stage_4_status={video.stage_4_status}, stage_5_status={video.stage_5_status}, stage_6_status={video.stage_6_status}"
            )
            video.stage_4_status = "pending"
            video.stage_5_status = "pending"
            video.stage_6_status = "pending"
            logger.debug("Video statuses set to 'pending'.")
        else:
            logger.error(
                f"Could not find matching video for transcript ID: {transcript_id}. Video status not reset."
            )

        db_session.commit()
        logger.info(
            f"Successfully reset status for transcript ID: {transcript_id}. It is now ready for reprocessing."
        )
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while resetting transcript ID {transcript_id}: {e}",
            exc_info=True,
        )
        db_session.rollback()
        raise


# --- Main Orchestration ---


def post_process_transcripts():
    """
    Main function to orchestrate the post-processing of transcripts
    by advancing them through all stages for each transcript.
    """
    logger.info("--- Starting Transcript Post-Processing Pipeline ---")
    db_session = db.SessionLocal()
    stop_processing = [
        False
    ]  # Use a mutable list to allow modification within function calls

    try:
        # Define the states that indicate a transcript is not fully processed
        processing_states = [
            "raw_transcript_received",
            "initial_cleaning_complete",
            "secondary_cleaning_complete",
            "metadata_generation_complete",
        ]
        logger.debug(f"Querying for transcripts in states: {processing_states}")

        # Find all transcripts that need processing
        transcripts_to_process = (
            db_session.query(db.TranscriptProcessing)
            .filter(db.TranscriptProcessing.status.in_(processing_states))
            .order_by(db.TranscriptProcessing.id)
            .all()
        )

        total_transcripts = len(transcripts_to_process)
        if total_transcripts == 0:
            logger.info("No transcripts found requiring post-processing.")
            return

        logger.info(
            f"Found {total_transcripts} transcripts to process through the pipeline."
        )

        for i, tp in enumerate(transcripts_to_process):
            if stop_processing[0]:
                logger.warning(
                    "Processing halted due to a critical error (e.g., API quota). Aborting pipeline."
                )
                break

            logger.info(
                f"--- Processing Transcript ID: {tp.id} (Item {i + 1}/{total_transcripts}) ---"
            )
            logger.debug(f"Current status of transcript {tp.id}: '{tp.status}'")

            # The pipeline stages are executed sequentially for each transcript.
            # If a stage fails, it raises an error, and the 'except' blocks below will catch it,
            # preventing subsequent stages for the *current* transcript from running.
            # The loop will then continue to the *next* transcript unless stop_processing is flagged.

            try:
                # Stage 1: Initial Cleaning
                if tp.status == "raw_transcript_received":
                    initial_cleaning(
                        tp.id,
                        current_index=i + 1,
                        total_count=total_transcripts,
                        stop_processing_flag=stop_processing,
                    )
                    db_session.refresh(tp)  # Refresh to get the new status

                # Stage 2: Secondary Cleaning (Paragraphing)
                if tp.status == "initial_cleaning_complete":
                    secondary_cleaning(
                        tp.id,
                        current_index=i + 1,
                        total_count=total_transcripts,
                        stop_processing_flag=stop_processing,
                    )
                    db_session.refresh(tp)

                # Stage 3: Metadata Generation
                if tp.status == "secondary_cleaning_complete":
                    gen_metadata(
                        tp.id,
                        current_index=i + 1,
                        total_count=total_transcripts,
                        stop_processing_flag=stop_processing,
                    )
                    db_session.refresh(tp)

                # Stage 4: Sermon Export File Generation
                if tp.status == "metadata_generation_complete":
                    export_sermon_file(
                        tp.id,
                        current_index=i + 1,
                        total_count=total_transcripts,
                        stop_processing_flag=stop_processing,
                    )
                    db_session.refresh(tp)

                logger.info(
                    f"--- Finished processing for Transcript ID: {tp.id}. Final status: '{tp.status}' ---"
                )

            except RuntimeError as e:
                # This catches errors raised by _execute_processing_stage,
                # logs them, and allows the loop to continue to the next transcript.
                logger.error(
                    f"A runtime error occurred while processing transcript {tp.id}. See logs above for details. Moving to the next transcript. Error: {e}"
                )
                # The status is already set by _execute_processing_stage, so we just continue.
                pass

    except Exception as e:
        logger.critical(
            f"A critical unexpected error occurred in the main processing loop: {e}",
            exc_info=True,
        )
    finally:
        logger.debug("Closing the main database session for the pipeline.")
        db_session.close()

    logger.info("--- Transcript Post-Processing Pipeline Finished ---")

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
        sermons_to_process = (
            session.query(db.TranscriptProcessing)
            .filter(db.TranscriptProcessing.status == "sermon_export_complete")
            .order_by(db.TranscriptProcessing.id)
            .all()
        )

        if not sermons_to_process:
            logger.info("No sermons are ready for the final automated edit.")
            return

        total_sermons = len(sermons_to_process)
        logger.info(f"Found {total_sermons} sermons to process for final edit.")

        editor = EditParagraphs()

        for i, sermon in enumerate(sermons_to_process):
            logger.info(
                f"--- Processing Sermon {i+1}/{total_sermons} (ID: {sermon.id}) for final edit ---"
            )
            logger.debug(f"Sermon {sermon.id} current status: {sermon.status}")

            # 1. Retrieve sermon text
            if not sermon.secondary_cleaning_path:
                logger.error(
                    f"Secondary cleaning path not found for sermon ID: {sermon.id}. Skipping final edit for this sermon."
                )
                continue
            try:
                logger.debug(
                    f"Reading sermon text from: {sermon.secondary_cleaning_path}"
                )
                with open(sermon.secondary_cleaning_path, "r") as f:
                    transcript_text = f.read()
                logger.debug(f"Successfully read sermon text for sermon {sermon.id}.")
            except FileNotFoundError:
                logger.error(
                    f"Sermon text file not found at {sermon.secondary_cleaning_path}. Skipping final edit for this sermon."
                )
                continue

            # 2. Retrieve outline from metadata
            outline_data = ""
            if sermon.metadata_path:
                try:
                    logger.debug(f"Reading metadata from: {sermon.metadata_path}")
                    with open(sermon.metadata_path, "r") as f:
                        metadata = json.load(f)
                        outline_data = metadata.get("outline", "")
                    logger.debug(f"Successfully loaded outline for sermon {sermon.id}.")
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    logger.warning(
                        f"Could not load outline for sermon {sermon.id}: {e}. Proceeding without it."
                    )
                    pass

            # 3. Prepare paragraph data
            paragraph_file_path = editor._get_paragraph_file_path(sermon)
            if not paragraph_file_path:
                logger.error(
                    f"Could not determine path for paragraphs.json for sermon {sermon.id}. Skipping."
                )
                continue
            logger.debug(
                f"Paragraphs JSON file path for sermon {sermon.id} is: {paragraph_file_path}"
            )

            paragraphs_data = None
            if paragraph_file_path.exists():
                try:
                    logger.debug(f"paragraphs.json file exists. Loading existing data.")
                    with open(paragraph_file_path, "r") as f:
                        paragraphs_data = json.load(f)
                    logger.debug("Successfully loaded existing paragraphs data.")
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(
                        f"Could not load or parse existing paragraphs.json for sermon {sermon.id}: {e}. Rebuilding data."
                    )
                    pass

            if not paragraphs_data:
                logger.debug(
                    "paragraphs.json data not loaded or file doesn't exist. Building new data structure."
                )
                paragraphs_data = editor._build_paragraphs_json_data(
                    transcript_text, outline_data
                )
                editor._save_paragraphs_to_file(paragraphs_data, paragraph_file_path)
                logger.debug("New paragraphs data built and saved.")

            # 4. Start the editing process
            logger.info(f"Starting final edit process for sermon {sermon.id}.")
            edited_transcript = editor.edit_paragraphs(
                paragraphs_data, paragraph_file_path
            )

            if edited_transcript:
                final_transcript_path = Path(sermon.raw_transcript_path).with_suffix(
                    ".edited.txt"
                )
                try:
                    logger.debug(
                        f"Saving final edited transcript to: {final_transcript_path}"
                    )
                    with open(final_transcript_path, "w") as f:
                        f.write(edited_transcript)
                    logger.info(
                        f"Successfully saved final edited transcript for sermon {sermon.id}."
                    )

                    # 5. Update status
                    logger.debug(
                        f"Updating status to 'final_edit_complete' for sermon {sermon.id}"
                    )
                    sermon.status = "final_edit_complete"
                    session.commit()
                    logger.info(f"Successfully updated status for sermon {sermon.id}.")

                except IOError as e:
                    logger.error(
                        f"Error saving final transcript for sermon {sermon.id}: {e}",
                        exc_info=True,
                    )
                    session.rollback()
            else:
                logger.error(
                    f"Final edit process for sermon {sermon.id} did not return an edited transcript. Status not updated."
                )

        logger.info("--- Automated Final Paragraph Editing Finished ---")

    except Exception as e:
        logger.critical(
            f"A critical unexpected error occurred during automated editing: {e}",
            exc_info=True,
        )
        session.rollback()
    finally:
        logger.debug("Closing database session for automated editing.")
        session.close()


class EditParagraphs:
    """Class to handle paragraph editing using Gemini API."""

    def __init__(self):
        """A class to handle paragraph-by-paragraph editing of a sermon."""
        self.sermon_selected = False  # This can be used to track state if needed
        self.ollama_client = OllamaClient()

    def select_sermon(self):
        """Selects and returns a list of sermon objects for editing."""
        logger.debug("Entering select_sermon method.")
        session = db.SessionLocal()
        try:
            # Define states for sermons ready for editing
            editable_states = [
                "metadata_generation_complete",
                "sermon_export_complete",
                "final_edit_complete",
            ]
            logger.debug(f"Querying for sermons in states: {editable_states}")

            sermons = (
                session.query(db.TranscriptProcessing)
                .filter(db.TranscriptProcessing.status.in_(editable_states))
                .order_by(db.TranscriptProcessing.id)
                .all()
            )

            if not sermons:
                logger.info("No sermons available for editing.")
                print(
                    "No sermons are currently in a state ready for editing (metadata complete or later)."
                )
                return []

            print("\n--- Available Sermons for Editing ---")
            for sermon in sermons:
                print(
                    f"  ID: {sermon.id:<5} Status: {sermon.status:<30} Path: ...{str(Path(sermon.raw_transcript_path).name)}"
                )
            print("-" * 35)

            selected_id_str = input(
                "Enter sermon ID to edit, 'all' for all, 'reset <ID>', or 'reset all': "
            )
            logger.info(f"User input for sermon selection: '{selected_id_str}'")

            if selected_id_str.lower() == "reset all":
                return self._reset_all_sermons_editing_state()

            if selected_id_str.lower().startswith("reset "):
                try:
                    reset_id = int(selected_id_str.split(" ")[1])
                    logger.debug(
                        f"Calling _reset_sermon_editing_state for ID: {reset_id}"
                    )
                    return self._reset_sermon_editing_state(reset_id)
                except (ValueError, IndexError):
                    logger.error("Invalid reset command from user. Use 'reset <ID>'.")
                    print("Invalid reset command. Use 'reset <ID>'.")
                    return []

            if selected_id_str.lower() == "all":
                logger.info("User selected to process all available sermons.")
                return sermons

            try:
                selected_id = int(selected_id_str)
                selected_sermon = next(
                    (s for s in sermons if s.id == selected_id), None
                )
                if selected_sermon:
                    logger.info(f"User selected sermon with ID: {selected_id}")
                    return [selected_sermon]
                else:
                    logger.warning(
                        f"No sermon found with ID: {selected_id}. Returning empty list."
                    )
                    print(f"No sermon found with ID: {selected_id}")
                    return []
            except ValueError:
                logger.error(
                    f"Invalid input from user: '{selected_id_str}'. Not a number, 'all', or 'reset'."
                )
                print(
                    "Invalid input. Please enter a number, 'all', or a reset command."
                )
                return []

        except Exception as e:
            logger.critical(
                f"An unexpected error occurred in select_sermon: {e}", exc_info=True
            )
            return []
        finally:
            logger.debug("Closing database session for select_sermon.")
            session.close()

    def _reset_sermon_editing_state(self, sermon_id):
        """Resets the editing state for a given sermon."""
        logger.debug(f"Entering _reset_sermon_editing_state for sermon ID: {sermon_id}")
        session = db.SessionLocal()
        try:
            sermon = (
                session.query(db.TranscriptProcessing)
                .filter(db.TranscriptProcessing.id == sermon_id)
                .first()
            )
            if not sermon:
                logger.warning(f"No sermon found with ID: {sermon_id} to reset.")
                print(f"No sermon found with ID: {sermon_id}.")
                return "RESET_FAILED"

            # Delete paragraphs.json file
            paragraph_file_path = self._get_paragraph_file_path(sermon)
            if paragraph_file_path and paragraph_file_path.exists():
                logger.debug(f"Deleting paragraphs.json file at: {paragraph_file_path}")
                os.remove(paragraph_file_path)
                logger.info(f"Deleted {paragraph_file_path} for sermon ID: {sermon_id}")
                print(f"Deleted paragraphs.json for sermon {sermon_id}.")
            else:
                logger.info(
                    f"No paragraphs.json found for sermon ID: {sermon_id}. Nothing to delete."
                )

            # Reset status in DB
            new_status = "sermon_export_complete"
            logger.debug(
                f"Updating status of sermon ID {sermon.id} from '{sermon.status}' to '{new_status}'"
            )
            sermon.status = new_status
            session.commit()
            logger.info(f"Successfully reset status of sermon ID: {sermon_id}.")
            print(f"Sermon ID: {sermon_id} has been reset and is ready for re-editing.")
            return "RESET_ACTION"

        except Exception as e:
            logger.error(f"Error resetting sermon ID {sermon_id}: {e}", exc_info=True)
            session.rollback()
            return "RESET_FAILED"
        finally:
            logger.debug(f"Closing database session for _reset_sermon_editing_state.")
            session.close()

    def _reset_all_sermons_editing_state(self):
        """Resets the editing state for all available sermons."""
        logger.debug("Entering _reset_all_sermons_editing_state.")
        session = db.SessionLocal()
        try:
            editable_states = [
                "metadata_generation_complete",
                "sermon_export_complete",
                "final_edit_complete",
            ]
            sermons_to_reset = (
                session.query(db.TranscriptProcessing)
                .filter(db.TranscriptProcessing.status.in_(editable_states))
                .all()
            )

            if not sermons_to_reset:
                logger.info("No sermons found in a resettable state.")
                print("No sermons found in a state that could be reset.")
                return "RESET_FAILED"

            logger.info(f"Found {len(sermons_to_reset)} sermons to reset.")
            print(f"Found {len(sermons_to_reset)} sermons to reset.")
            # We call the single reset function which now handles its own session.
            # This is less efficient but ensures logical encapsulation.
            session.close()  # Close the session used for querying

            for sermon in sermons_to_reset:
                self._reset_sermon_editing_state(sermon.id)

            logger.info("All available sermons have been reset.")
            print("All available sermons have been reset.")
            return "RESET_ACTION"

        except Exception as e:
            logger.critical(
                f"An error occurred while resetting all sermons: {e}", exc_info=True
            )
            if session.is_active:
                session.rollback()
            return "RESET_FAILED"
        finally:
            if session.is_active:
                logger.debug(
                    "Closing database session for _reset_all_sermons_editing_state."
                )
                session.close()

    def _get_paragraph_file_path(self, selected_sermon):
        """Returns the path for the paragraphs.json file for a given sermon."""
        if not selected_sermon or not selected_sermon.raw_transcript_path:
            return None
        return Path(selected_sermon.raw_transcript_path).parent / "paragraphs.json"

    def _build_paragraphs_json_data(self, transcript_text, outline):
        """Builds the initial data structure for paragraphs.json."""
        logger.debug("Entering _build_paragraphs_json_data.")
        # Initialize paths for prompts directory
        BASE_DIR = Path(__file__).resolve().parent
        PROMPTS_DIR = BASE_DIR / "prompts"

        # load prompt templates
        standard_prompt_path = PROMPTS_DIR / "edit-paragraph-standard.txt"
        first_paragraph_prompt_path = PROMPTS_DIR / "edit-paragraph-first.txt"
        last_paragraph_prompt_path = PROMPTS_DIR / "edit-paragraph-last.txt"

        paragraphs = transcript_text.split("\n\n")
        paragraphs_data = []
        total_paragraphs = len(paragraphs)
        logger.info(f"Building paragraph data for {total_paragraphs} paragraphs.")

        for i, paragraph in enumerate(paragraphs):
            prompt = ""
            try:
                logger.debug(f"Processing paragraph {i+1}/{total_paragraphs}")
                if i == 0 and total_paragraphs > 1:
                    prompt_template = first_paragraph_prompt_path.read_text()
                    prompt = prompt_template.format(
                        PARAGRAPH_TARGET=paragraph, PARAGRAPH_NEXT=paragraphs[i + 1]
                    )
                elif i == total_paragraphs - 1 and total_paragraphs > 1:
                    prompt_template = last_paragraph_prompt_path.read_text()
                    prompt = prompt_template.format(
                        PARAGRAPH_TARGET=paragraph, PARAGRAPH_PREV=paragraphs[i - 1]
                    )
                elif total_paragraphs > 1:
                    prompt_template = standard_prompt_path.read_text()
                    prompt = prompt_template.format(
                        PARAGRAPH_TARGET=paragraph,
                        PARAGRAPH_PREV=paragraphs[i - 1],
                        PARAGRAPH_NEXT=paragraphs[i + 1],
                    )
                else:  # Handle case with only one paragraph
                    prompt_template = (
                        first_paragraph_prompt_path.read_text()
                    )  # Or a specific single-paragraph prompt
                    prompt = prompt_template.format(
                        PARAGRAPH_TARGET=paragraph, PARAGRAPH_NEXT=""
                    )

                paragraph_entry = {
                    "index": i,
                    "original": paragraph,
                    "prompt": prompt,
                    "edited": None,
                }
                paragraphs_data.append(paragraph_entry)

            except FileNotFoundError as e:
                logger.error(
                    f"Error reading prompt file for paragraph {i+1}: {e}", exc_info=True
                )
                paragraphs_data.append(
                    {
                        "index": i,
                        "original": paragraph,
                        "prompt": "[PROMPT FILE NOT FOUND]",
                        "edited": None,
                    }
                )
            except Exception as e:
                logger.error(
                    f"Error creating prompt for paragraph {i + 1}: {e}", exc_info=True
                )
                paragraphs_data.append(
                    {
                        "index": i,
                        "original": paragraph,
                        "prompt": "[ERROR CREATING PROMPT]",
                        "edited": None,
                    }
                )

        logger.info(
            f"Finished building paragraph data structure for {total_paragraphs} paragraphs."
        )
        return paragraphs_data

    def build_paragraph_editing_score(
        self, original_paragraph_dict, edited_paragraph_dict
    ):
        """Compares original and edited paragraphs to build an editing score."""
        logger.warning("build_paragraph_editing_score is not yet implemented.")
        # build json file detaining the differences
        pass

    def _save_paragraphs_to_file(self, data, file_path):
        """Saves the paragraph data to the JSON file."""
        logger.debug(f"Attempting to save paragraph data to: {file_path}")
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=4)
            logger.info(
                f"Successfully saved progress for {len(data)} paragraphs to {file_path}"
            )
        except Exception as e:
            logger.error(f"Failed to save progress to {file_path}: {e}", exc_info=True)

    def edit_paragraphs(self, paragraphs_data, paragraph_file_path):
        """Processes paragraphs that need editing and saves progress intermittently."""
        logger.debug("Entering edit_paragraphs method.")

        # Filter to get only the paragraphs that need editing
        paragraphs_to_process = [p for p in paragraphs_data if p.get("edited") is None]
        num_to_process = len(paragraphs_to_process)
        total_paragraphs = len(paragraphs_data)

        if num_to_process == 0:
            logger.info(
                "All paragraphs have already been edited. Reassembling transcript."
            )
            # Reassemble the full transcript from the loaded data
            edited_transcript = "\n\n".join(
                p.get("edited", p.get("original", "")) for p in paragraphs_data
            )
            return edited_transcript

        logger.info(
            f"Starting sequential processing of {num_to_process} remaining paragraphs out of {total_paragraphs} total."
        )

        for i, paragraph_item in enumerate(paragraphs_to_process):
            index = paragraph_item.get("index")
            prompt = paragraph_item.get("prompt")
            original_paragraph = paragraph_item.get("original")

            logger.info(
                f"Processing paragraph {index + 1}/{total_paragraphs} ({i + 1}/{num_to_process} in this run)."
            )

            if not prompt or prompt.startswith("[ERROR"):
                logger.warning(
                    f"No valid prompt for paragraph {index}. Using original text."
                )
                paragraph_item["edited"] = original_paragraph
                self._save_paragraphs_to_file(paragraphs_data, paragraph_file_path)
                continue

            max_retries = 3
            for attempt in range(max_retries):
                logger.debug(
                    f"Attempt {attempt + 1}/{max_retries} for paragraph {index}."
                )
                try:
                    edited_text = self.ollama_client.submit_prompt(prompt)

                    if attempt > 0:
                        logger.info(
                            f"Successfully processed paragraph {index} on attempt {attempt + 1}."
                        )
                    else:
                        logger.debug(
                            f"Successfully processed paragraph {index} on first attempt."
                        )

                    # Update the shared data structure
                    paragraph_item["edited"] = edited_text
                    # Save progress after each successful edit
                    self._save_paragraphs_to_file(paragraphs_data, paragraph_file_path)
                    break  # Exit retry loop on success

                except OllamaProcessingError as e:
                    logger.critical(
                        f"!!! CRITICAL: Ollama API processing issue. Halting all editing. Error: {e}.",
                        exc_info=True,
                    )
                    return None  # Stop editing and return early

                except RuntimeError as e:
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for paragraph {index}: {e}"
                    )
                    if attempt == max_retries - 1:
                        logger.error(
                            f"All {max_retries} attempts failed for paragraph {index}. The original text will be used."
                        )
                        # 'edited' remains None, will be handled during final reassembly

        logger.info("Paragraph processing run complete.")

        # Final reassembly of the transcript
        logger.debug("Reassembling final transcript.")
        edited_transcript_list = []
        for p in sorted(paragraphs_data, key=lambda x: x["index"]):
            if p.get("edited") is not None:
                edited_transcript_list.append(p["edited"])
            else:
                logger.warning(
                    f"Using original text for paragraph {p['index']} as it was not successfully edited."
                )
                edited_transcript_list.append(p["original"])

        final_transcript = "\n\n".join(edited_transcript_list)
        logger.info(
            f"Final transcript reassembled. Total length: {len(final_transcript)} characters."
        )
        return final_transcript

    def run_editor(self):
        """Orchestrates the sermon editing process for one or more sermons with resumability."""
        logger.info("--- Starting Interactive Sermon Editor ---")

        sermons_to_process = self.select_sermon()

        if sermons_to_process == "RESET_ACTION":
            logger.info("Sermon editing state was reset. Aborting further editing.")
            print(
                "Reset action completed. Please run the editor again to select a sermon."
            )
            return
        if sermons_to_process == "RESET_FAILED":
            logger.error("Sermon editing state reset failed. Aborting further editing.")
            print("Reset action failed. Please check the logs.")
            return
        if not sermons_to_process:
            logger.info("No sermons selected for editing. Exiting.")
            print("No sermons selected.")
            return

        final_edited_text = None
        session = db.SessionLocal()

        try:
            total_sermons = len(sermons_to_process)
            logger.info(f"Processing {total_sermons} selected sermon(s).")

            for i, sermon in enumerate(sermons_to_process):
                logger.info(
                    f"--- Processing Sermon {i+1}/{total_sermons} (ID: {sermon.id}) ---"
                )

                # 1. Retrieve sermon text
                if (
                    not sermon.secondary_cleaning_path
                    or not Path(sermon.secondary_cleaning_path).exists()
                ):
                    logger.error(
                        f"Secondary cleaning path not found for sermon ID: {sermon.id}. Skipping."
                    )
                    print(
                        f"ERROR: Source text file not found for sermon {sermon.id}. Cannot edit."
                    )
                    continue
                with open(sermon.secondary_cleaning_path, "r") as f:
                    transcript_text = f.read()

                # 2. Retrieve outline from metadata
                outline_data = ""
                if sermon.metadata_path and Path(sermon.metadata_path).exists():
                    try:
                        with open(sermon.metadata_path, "r") as f:
                            metadata = json.load(f)
                            outline_data = metadata.get("outline", "")
                    except (json.JSONDecodeError, FileNotFoundError) as e:
                        logger.warning(
                            f"Could not load outline for sermon {sermon.id}: {e}. Proceeding without it."
                        )

                # 3. Prepare paragraph data
                paragraph_file_path = self._get_paragraph_file_path(sermon)
                paragraphs_data = None
                if paragraph_file_path and paragraph_file_path.exists():
                    logger.debug(
                        f"Found existing paragraphs file: {paragraph_file_path}"
                    )
                    try:
                        with open(paragraph_file_path, "r") as f:
                            paragraphs_data = json.load(f)
                        logger.info(
                            f"Resuming from existing paragraphs.json for sermon {sermon.id}."
                        )
                    except (json.JSONDecodeError, IOError) as e:
                        logger.warning(
                            f"Could not load or parse {paragraph_file_path}. Rebuilding. Error: {e}"
                        )

                if not paragraphs_data:
                    logger.info(
                        f"No existing paragraphs.json found for sermon {sermon.id}. Building new data."
                    )
                    paragraphs_data = self._build_paragraphs_json_data(
                        transcript_text, outline_data
                    )
                    self._save_paragraphs_to_file(paragraphs_data, paragraph_file_path)

                # 4. Start the editing process
                edited_transcript = self.edit_paragraphs(
                    paragraphs_data, paragraph_file_path
                )

                if edited_transcript:
                    final_transcript_path = (
                        Path(sermon.raw_transcript_path).parent / "edited.txt"
                    )
                    with open(final_transcript_path, "w") as f:
                        f.write(edited_transcript)
                    logger.info(
                        f"Successfully saved final edited transcript to: {final_transcript_path}"
                    )

                    # 5. Update status
                    sermon_in_session = (
                        session.query(db.TranscriptProcessing)
                        .filter(db.TranscriptProcessing.id == sermon.id)
                        .first()
                    )
                    if sermon_in_session:
                        logger.debug(
                            f"Updating status to 'final_edit_complete' for sermon {sermon.id}"
                        )
                        sermon_in_session.status = "final_edit_complete"
                        session.commit()
                        logger.info(
                            f"Successfully updated status for sermon {sermon.id}"
                        )

                    final_edited_text = edited_transcript
                    print(f"\n--- Editing complete for Sermon ID: {sermon.id} ---")
                    print(f"Final transcript saved to: {final_transcript_path}")

                else:
                    logger.error(
                        f"Editing failed for sermon {sermon.id}. No transcript was returned. Check for critical errors above."
                    )
                    print(
                        f"ERROR: Editing failed for sermon {sermon.id}. The transcript was not saved."
                    )

        except Exception as e:
            logger.critical(
                f"An unexpected error occurred during the editor run: {e}",
                exc_info=True,
            )
            if session.is_active:
                session.rollback()
        finally:
            logger.debug("Closing database session for run_editor.")
            if session.is_active:
                session.close()
            logger.info("--- Interactive Sermon Editor Finished ---")

        return final_edited_text
