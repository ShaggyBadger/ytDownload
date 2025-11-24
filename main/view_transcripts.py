from db import SessionLocal, TranscriptProcessing, Video
from pathlib import Path
import os
import post_process_transcripts

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
                print("No transcripts found to display.")
                input("Press Enter to return to the main menu...")
                return

            print("\n--- Available Transcripts ---")
            # Unpack the tuple returned by the query
            for transcript, yt_id in results:
                print(f"ID: {transcript.id}, YT_ID: {yt_id}, Status: {transcript.status}")
            print("--------------------------")

            print("\n--- Transcript Menu ---")
            print("1: View a specific transcript")
            print("2: Reset all transcripts")
            print("q: Return to main menu")
            
            main_choice = input("Enter your choice: ")

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
                        print("Invalid ID. Please try again.")
                except ValueError:
                    print("Invalid input. Please enter a number.")

            elif main_choice == '2':
                reset_all_transcripts()

            elif main_choice.lower() == 'q':
                break
            
            else:
                print("Invalid choice, please try again.")

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


def reset_all_transcripts():
    """
    Deletes all processed files for all transcripts and resets their status.
    """
    db = SessionLocal()
    try:
        transcripts = db.query(TranscriptProcessing).all()
        if not transcripts:
            print("No transcripts to reset.")
            return
        
        confirm = input(f"Are you sure you want to reset all {len(transcripts)} transcripts? This is irreversible. (y/n): ")
        if confirm.lower() != 'y':
            print("Reset cancelled.")
            return

        for transcript in transcripts:
            delete_and_reset_transcript(transcript, db)
        
        print(f"\n--- All {len(transcripts)} transcripts have been reset. ---")

    finally:
        db.close()


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

    # Reset paths and status on TranscriptProcessing
    transcript.book_ready_path = None
    transcript.final_pass_path = None
    transcript.metadata_path = None
    transcript.initial_cleaning_path = None
    transcript.secondary_cleaning_path = None
    transcript.status = "raw_transcript_received"

    # Also reset status on the Video table
    video = db.query(Video).filter(Video.id == transcript.video_id).first()
    if video:
        print(f"Resetting video status for video ID: {video.id}")
        video.stage_4_status = "pending"
        video.stage_5_status = "pending"
        video.stage_6_status = "pending"
    else:
        print(f"Could not find matching video for transcript ID: {transcript.id}")
    
    db.commit()
    print(f"Transcript ID: {transcript.id} has been reset and is ready for reprocessing.")
