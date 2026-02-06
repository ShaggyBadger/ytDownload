from pathlib import Path
import os
from db import SessionLocal, TranscriptProcessing, Video
from logger import setup_logger
from post_process_transcripts import reset_transcript_status

logger = setup_logger(__name__)


def delete_transcript_files(transcript):
    """Deletes all generated post-processing files for a transcript."""
    logger.info(f"Attempting to delete files for transcript ID: {transcript.id}")

    # These paths are stored directly in the database
    files_to_delete = [
        transcript.initial_cleaning_path,
        transcript.secondary_cleaning_path,
        transcript.metadata_path,
        transcript.final_pass_path,
        transcript.book_ready_path,
        transcript.python_scrub_path,
    ]

    # These paths need to be constructed
    if transcript.raw_transcript_path:
        video_dir = Path(transcript.raw_transcript_path).parent

        # sermon_export.txt
        files_to_delete.append(str(video_dir / "sermon_export.txt"))

        # paragraphs.json
        files_to_delete.append(str(video_dir / "paragraphs.json"))

        # .edited.txt
        files_to_delete.append(
            str(Path(transcript.raw_transcript_path).with_suffix(".edited.txt"))
        )

    for file_path in files_to_delete:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
            except OSError as e:
                logger.error(f"Error deleting file {file_path}: {e}")
        elif file_path:
            logger.warning(f"File not found, skipping delete: {file_path}")


def choose_and_reset_sermon():
    """Lists all transcripts and prompts the user to select one to reset."""
    db_session = SessionLocal()
    try:
        logger.info("--- Select a Sermon to Reset ---")
        results = (
            db_session.query(TranscriptProcessing, Video.yt_id)
            .join(Video, TranscriptProcessing.video_id == Video.id)
            .order_by(TranscriptProcessing.id)
            .all()
        )

        if not results:
            logger.info("No transcripts found to reset.")
            input("Press Enter to return to the main menu...")
            return

        logger.info("--- Available Transcripts ---")
        for transcript, yt_id in results:
            logger.info(
                f"ID: {transcript.id}, YT_ID: {yt_id}, Status: {transcript.status}"
            )
        logger.info("--------------------------")

        choice = input("Enter the ID of the transcript to reset (or 'b' to go back): ")
        if choice.lower() == "b":
            return

        transcript_id = int(choice)
        transcript_to_reset = (
            db_session.query(TranscriptProcessing)
            .filter(TranscriptProcessing.id == transcript_id)
            .first()
        )

        if transcript_to_reset:
            confirm = input(
                f"Are you sure you want to delete all generated files and reset transcript ID {transcript_id}? (y/n): "
            )
            if confirm.lower() == "y":
                # 1. Delete generated files
                delete_transcript_files(transcript_to_reset)
                # 2. Reset DB status
                reset_transcript_status(transcript_id, db_session)
                logger.info(
                    f"--- Transcript ID: {transcript_id} has been reset and is ready for reprocessing. ---"
                )
            else:
                logger.info("Reset cancelled.")
        else:
            logger.error(f"Transcript with ID {transcript_id} not found.")

    except ValueError:
        logger.warning("Invalid input. Please enter a number.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        db_session.close()
