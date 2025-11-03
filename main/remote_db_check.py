
import json
from pathlib import Path
import db
from desktop_connection_utility import sftp_put, run_remote_cmd, sftp_get

# Define remote paths
REMOTE_PROJECT_DIR = "/home/alexander/pyProjects/sermonTranscriber"
REMOTE_SCRIPT_PATH = f"{REMOTE_PROJECT_DIR}/remote_check.py"
LOCAL_SCRIPT_PATH = Path(__file__).parent / "remote_check.py"
LOCAL_TRANSCRIPTS_DIR = Path(__file__).parent / "transcripts"

def get_status_char(status):
    """Returns a single character representation of a status."""
    if not status:
        return ' '
    return status[0].upper()

def check_remote_status_and_fetch_completed():
    """
    Checks the status of transcriptions on the remote desktop and fetches
    any completed files.
    """
    db_session = db.SessionLocal()
    try:
        # Ensure the local transcripts directory exists
        LOCAL_TRANSCRIPTS_DIR.mkdir(exist_ok=True)

        # 1. Upload the remote_check.py script
        print(f"Uploading {LOCAL_SCRIPT_PATH.name} to {REMOTE_SCRIPT_PATH}...")
        sftp_put(str(LOCAL_SCRIPT_PATH), REMOTE_SCRIPT_PATH)

        # 2. Execute the script on the remote machine
        print("Executing remote script to check database status...")
        remote_cmd = f"cd {REMOTE_PROJECT_DIR} && source venvFiles/bin/activate && python3 {REMOTE_SCRIPT_PATH}"
        json_output = run_remote_cmd(remote_cmd)

        # 3. Parse the JSON output
        try:
            remote_statuses = json.loads(json_output)
        except json.JSONDecodeError:
            print("Error: Could not decode JSON from remote script.")
            print("Raw output:", json_output)
            return

        if not remote_statuses:
            print("No files found in the remote database.")
            return

        if "error" in remote_statuses[0]:
            print("Error checking remote status:", remote_statuses[0]["error"])
            return

        print("Successfully retrieved status from remote desktop.")
        print("\n--- Remote File Status ---")
        for remote_status in remote_statuses:
            mp3_id = remote_status.get("mp3Id")
            status = remote_status.get("status")
            status_char = get_status_char(status)
            print(f"  ID: {mp3_id:<3} [{status_char}] - {status}")

        # 4. Process the statuses and fetch completed files
        for remote_status in remote_statuses:
            video_id = remote_status.get("mp3Id")
            status = remote_status.get("status")
            transcript_path = remote_status.get("transcript_path")
            transcript_exists = remote_status.get("transcript_exists")

            if status == "complete" and transcript_exists:
                video = db_session.query(db.Video).filter(db.Video.id == video_id).first()
                if video and video.stage_3_status != "complete":
                    print(f"Found completed transcription for video ID: {video_id}")
                    local_transcript_path = LOCAL_TRANSCRIPTS_DIR / Path(transcript_path).name

                    # Download the transcript file
                    print(f"Downloading {transcript_path} to {local_transcript_path}...")
                    sftp_get(transcript_path, str(local_transcript_path))

                    # Update the local database
                    video.stage_3_status = "complete"
                    video.transcript_path = str(local_transcript_path)
                    db_session.commit()
                    print(f"Updated local database for video ID: {video_id}")

    finally:
        db_session.close()

if __name__ == "__main__":
    check_remote_status_and_fetch_completed()
