import process_links
import fetch_mp3
import db_info
import transcribe

def display_menu():
    """Displays the main menu."""
    print("\n--- Main Menu ---")
    print("1: Process video links into the database")
    print("2: Download and Trim MP3s")
    print("3: Display DB Status")
    print("4: Transcribe Audio")
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
            transcribe.process_transcription()
        elif choice.lower() == 'q':
            print("Exiting.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == '__main__':
    main()

