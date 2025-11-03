from desktop_connection_utility import run_remote_cmd
import db

REMOTE_PROJECT_DIR = "/home/alexander/pyProjects/sermonTranscriber"

def process_transcription():
    """
    Triggers the remote transcription process for videos that are ready.
    """
    db_session = db.SessionLocal()
    try:
        # Check for videos ready for transcription
        videos_to_process = db_session.query(db.Video).filter(
            db.Video.stage_2_status == "completed",
            db.Video.stage_3_status.notin_(["complete", "completed"])
        ).all()

        if not videos_to_process:
            print("\nNo videos ready for transcription.")
            return

        print(f"\nFound {len(videos_to_process)} videos ready for transcription.")
        print("Triggering remote processing...")

        # Command to start the transcription process in the background
        remote_cmd = (
            f"cd {REMOTE_PROJECT_DIR}/main && "
            f"source ../venvFiles/bin/activate && "
            f"nohup python3 controller.py > /dev/null 2>&1 &"
        )
        print(f"Running remote command: {remote_cmd}")
        run_remote_cmd(remote_cmd)

        # Update the database
        for video in videos_to_process:
            video.stage_3_status = "processing"
        db_session.commit()

        print("\nRemote transcription process initiated successfully in the background.")

    finally:
        db_session.close()
