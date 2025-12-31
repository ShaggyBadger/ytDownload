import process_links
import fetch_mp3
import db_info
import transfer_files
import remote_db_info
import remote_db_check
import post_process_transcripts
import view_transcripts
import sermon_exporter
import clean_sermon_transcripts
from db import Base, engine
import migration
import logger_config

# Setup logging
logger_config.setup_logging()

# Run any pending database migrations first.
migration.run_migration()

# Create all tables in the database if they don't exist.
# This is idempotent.
Base.metadata.create_all(bind=engine)

def display_menu():
    """Displays the main menu."""
    print("\n--- Main Menu ---")
    print("1: Process video links into the database")
    print("2: Download and Trim MP3s")
    print("3: Display DB Status")
    print("4: Deploy Transcription Jobs")
    print("5: Check remote DB status and fetch completed transcripts")
    print("6: Post-process transcripts")
    print("7: View Transcripts")
    print("8: Clean Sermon Transcripts up")
    print("q: Quit")
    print("-----------------")

def main():
    """Main function to run the controller."""
    while True:
        display_menu()
        choice = input("Enter your choice: ")

        if choice == '1':
            process_links.process_video_links()
        elif choice == '2':
            selected_videos = fetch_mp3.select_videos_to_process()
            fetch_mp3.process_selected_videos(selected_videos)
        elif choice == '3':
            db_info.display_db_info()
        elif choice == '4':
            transfer_files.prepare_and_transfer_files()
        elif choice == '5':
            remote_db_check.check_remote_status_and_fetch_completed()
        elif choice == '6':
            post_process_transcripts.post_process_transcripts()
        elif choice == '7':
            view_transcripts.view_transcripts()
        elif choice == '8':
            clean_sermon_transcripts.clean_sermon_transcripts()
        elif choice.lower() == 'q':
            print("Exiting.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == '__main__':
    main()