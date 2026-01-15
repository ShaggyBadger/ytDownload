from db import SessionLocal, TranscriptProcessing, Video
import os # Keep os for Path usage in _get_paragraph_file_path if needed
from pathlib import Path
import post_process_transcripts
from logger import setup_logger

logger = setup_logger(__name__)

def view_transcripts():
    """
    Main function to view transcripts.
    """
    while True:
        db = SessionLocal()
        try:
            # Join TranscriptProcessing with Video to get access to yt_id
            results = db.query(TranscriptProcessing, Video.yt_id).join(Video, TranscriptProcessing.video_id == Video.id).all()
            
            if not results:
                logger.info("No transcripts found to display.")
                input("Press Enter to return to the main menu...")
                return

            logger.info("--- Available Transcripts ---")
            # Unpack the tuple returned by the query
            for transcript, yt_id in results:
                logger.info(f"ID: {transcript.id}, YT_ID: {yt_id}, Status: {transcript.status}")
            logger.info("--------------------------")

            logger.info("--- Transcript Menu ---")
            logger.info("1: View a specific transcript")
            logger.info("2: Reset all transcripts")
            logger.info("q: Return to main menu")
            
            main_choice = input("Enter your choice: ")
            logger.info(f"User choice: {main_choice}")

            if main_choice == '1':
                try:
                    choice = input("Enter the ID of the transcript to view (or 'b' to go back): ")
                    if choice.lower() == 'b':
                        continue
                    transcript_id = int(choice)
                    selected_transcript = db.query(TranscriptProcessing).filter(TranscriptProcessing.id == transcript_id).first()
                    if selected_transcript:
                        display_transcript_files(selected_transcript)
                    else:
                        logger.warning("Invalid ID. Please try again.")
                except ValueError:
                    logger.warning("Invalid input. Please enter a number.")

            elif main_choice == '2':
                reset_all_transcripts()

            elif main_choice.lower() == 'q':
                break
            
            else:
                logger.warning("Invalid choice, please try again.")

        finally:
            db.close()

def display_transcript_files(transcript):
    """
    Displays the content of the transcript files.
    """
    logger.info(f"--- Displaying files for Transcript ID: {transcript.id} ---")

    file_paths = {
        "Metadata": transcript.metadata_path,
        "Initial Cleaning": transcript.initial_cleaning_path,
        "Book Ready": transcript.book_ready_path
    }

    for name, file_path in file_paths.items():
        logger.info(f"--- {name} ---")
        if file_path and Path(file_path).exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                logger.info(f.read())
        else:
            logger.info(f"File not found or path not set for {name}.")
        logger.info("--------------------")
        input("Press Enter to continue...")

    while True:
        logger.info("What would you like to do?")
        logger.info("1: Run the book cleanup process")
        logger.info("2: Reset this transcript")
        logger.info("q: Quit")
        choice = input("Enter your choice: ")
        logger.info(f"User choice: {choice}")

        if choice == '1':
            logger.info("--- Running book cleanup process ---")
            post_process_transcripts.llm_book_cleanup(transcript.id)
            post_process_transcripts.update_metadata_file(transcript.id)
            logger.info("--- Book cleanup process complete ---")
            break
        elif choice == '2':
            db = SessionLocal()
            try:
                # Re-fetch the transcript object in the new session
                transcript_to_reset = db.query(TranscriptProcessing).filter(TranscriptProcessing.id == transcript.id).first()
                if transcript_to_reset:
                    post_process_transcripts.reset_transcript_status(transcript_to_reset.id, db)
                else:
                    logger.error(f"Could not find transcript with ID: {transcript.id} to reset.")
            finally:
                db.close()
            break
        elif choice.lower() == 'q':
            break
        else:
            logger.warning("Invalid choice. Please try again.")


def reset_all_transcripts():
    """
    Resets the status of all transcripts in the database.
    """
    db = SessionLocal()
    try:
        transcripts = db.query(TranscriptProcessing).all()
        if not transcripts:
            logger.info("No transcripts to reset.")
            return
        
        confirm = input(f"Are you sure you want to reset all {len(transcripts)} transcripts? (y/n): ")
        if confirm.lower() != 'y':
            logger.info("Reset cancelled.")
            return

        for transcript in transcripts:
            post_process_transcripts.reset_transcript_status(transcript.id, db)
        
        logger.info(f"--- All {len(transcripts)} transcripts have been reset. ---")

    finally:
        db.close()

