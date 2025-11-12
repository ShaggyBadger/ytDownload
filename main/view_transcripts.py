from db import SessionLocal, TranscriptProcessing
from pathlib import Path
import os
import post_process_transcripts

def view_transcripts():
    """
    Main function to view transcripts.
    """
    db = SessionLocal()
    try:
        transcripts = db.query(TranscriptProcessing).all()
        if not transcripts:
            print("No transcripts found to display.")
            return

        print("\n--- Available Transcripts ---")
        for transcript in transcripts:
            print(f"ID: {transcript.id}, Video ID: {transcript.video_id}, Status: {transcript.status}")
        print("--------------------------")

        while True:
            try:
                choice = input("Enter the ID of the transcript to view (or 'q' to quit): ")
                if choice.lower() == 'q':
                    break
                transcript_id = int(choice)
                selected_transcript = db.query(TranscriptProcessing).filter(TranscriptProcessing.id == transcript_id).first()
                if selected_transcript:
                    display_transcript_files(selected_transcript)
                    break
                else:
                    print("Invalid ID. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")
    finally:
        db.close()

def display_transcript_files(transcript):
    """
    Displays the content of the transcript files.
    """
    print(f"\n--- Displaying files for Transcript ID: {transcript.id} ---")

    file_paths = {
        "Metadata": transcript.metadata_path,
        "Initial Cleaning": transcript.initial_cleaning_path,
        "Book Ready": transcript.book_ready_path
    }

    for name, file_path in file_paths.items():
        print(f"\n--- {name} ---")
        if file_path and Path(file_path).exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                print(f.read())
        else:
            print(f"File not found or path not set for {name}.")
        print("--------------------")
        input("Press Enter to continue...")

    while True:
        print("\nWhat would you like to do?")
        print("1: Run the book cleanup process")
        print("2: Delete and reset this transcript")
        print("q: Quit")
        choice = input("Enter your choice: ")

        if choice == '1':
            print("\n--- Running book cleanup process ---")
            post_process_transcripts.llm_book_cleanup(transcript.id)
            post_process_transcripts.update_metadata_file(transcript.id)
            print("--- Book cleanup process complete ---")
            break
        elif choice == '2':
            db = SessionLocal()
            try:
                # Re-fetch the transcript object in the new session
                transcript_to_delete = db.query(TranscriptProcessing).filter(TranscriptProcessing.id == transcript.id).first()
                if transcript_to_delete:
                    delete_and_reset_transcript(transcript_to_delete, db)
                else:
                    print(f"Could not find transcript with ID: {transcript.id} to delete.")
            finally:
                db.close()
            break
        elif choice.lower() == 'q':
            break
        else:
            print("Invalid choice. Please try again.")


def delete_and_reset_transcript(transcript, db):
    """
    Deletes the processed files for a transcript and resets its status.
    """
    print(f"\n--- Resetting transcript ID: {transcript.id} ---")

    files_to_delete = [
        transcript.book_ready_path,
        transcript.final_pass_path,
        transcript.metadata_path,
        transcript.initial_cleaning_path,
        transcript.secondary_cleaning_path
    ]

    for file_path in files_to_delete:
        if file_path and Path(file_path).exists():
            try:
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
            except OSError as e:
                print(f"Error deleting file {file_path}: {e}")

    # Reset paths and status
    transcript.book_ready_path = None
    transcript.final_pass_path = None
    transcript.metadata_path = None
    transcript.initial_cleaning_path = None
    transcript.secondary_cleaning_path = None
    transcript.status = "raw_transcript_received"
    
    db.commit()
    print(f"Transcript ID: {transcript.id} has been reset and is ready for reprocessing.")
