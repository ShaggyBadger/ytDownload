import json
from pathlib import Path
import db
from utils import get_video_paths
from desktop_connection_utility import sftp_put, run_remote_cmd, sftp_get
from logger import setup_logger

logger = setup_logger(__name__)

# Define remote paths
REMOTE_PROJECT_DIR = "/home/alexander/pyProjects/sermonTranscriber"
REMOTE_SCRIPT_PATH = f"{REMOTE_PROJECT_DIR}/remote_check.py"
LOCAL_SCRIPT_PATH = Path(__file__).parent / "remote_check.py"
LOCAL_TRANSCRIPTS_DIR = Path(__file__).parent / "transcripts" # This might be deprecated soon

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
        # 1. Upload the remote_check.py script
        logger.info(f"Uploading {LOCAL_SCRIPT_PATH.name} to {REMOTE_SCRIPT_PATH}...")
        sftp_put(str(LOCAL_SCRIPT_PATH), REMOTE_SCRIPT_PATH)

        # 2. Execute the script on the remote machine
        logger.info("Executing remote script to check database status...")
        remote_cmd = f"cd {REMOTE_PROJECT_DIR} && source venvFiles39/bin/activate && python3 {REMOTE_SCRIPT_PATH}"
        json_output = run_remote_cmd(remote_cmd)

        # 3. Parse the JSON output
        try:
            remote_statuses = json.loads(json_output)
        except json.JSONDecodeError:
            logger.error("Could not decode JSON from remote script.")
            logger.error(f"Raw output: {json_output}")
            return

        if not remote_statuses:
            logger.info("No files found in the remote database.")
            return

        if "error" in remote_statuses[0]:
            logger.error(f"Error checking remote status: {remote_statuses[0]['error']}")
            return

        logger.info("Successfully retrieved status from remote desktop.")
        logger.info("--- Remote File Status ---")
        for remote_status in remote_statuses:
            mp3_id = remote_status.get("mp3_id")
            status = remote_status.get("status")
            status_char = get_status_char(status)
            logger.info(f"  ID: {mp3_id:<3} [{status_char}] - {status}")

        # 4. Process the statuses and fetch/verify completed files
        for remote_status in remote_statuses:
            video_id = remote_status.get("mp3_id")
            status = remote_status.get("status")
            remote_transcript_path = remote_status.get("transcript_path") # Renamed for clarity
            transcript_exists = remote_status.get("transcript_exists")

            if status == "complete" and transcript_exists:
                video = db_session.query(db.Video).filter(db.Video.id == video_id).first()
                if video:
                    paths = get_video_paths(video) # <--- Get all paths
                    if not paths:
                        logger.error(f"Could not get paths for video {video.id} - {video.yt_id}")
                        continue

                    # local_transcript_path should now be the raw_transcript_path from our utils
                    local_transcript_path = Path(paths["raw_transcript_path"])

                    # Download if it doesn't exist
                    if not local_transcript_path.exists():
                        logger.info(f"Local transcript for video ID {video_id} not found. Redownloading from {remote_transcript_path}...")
                        sftp_get(remote_transcript_path, str(local_transcript_path))
                        logger.info(f"Downloaded transcript to {local_transcript_path}")

                    made_changes = False
                    # Update video status for stage 3 if needed
                    if video.stage_3_status != "complete":
                        video.stage_3_status = "complete"
                        video.transcript_path = paths["transcript_path"] # <--- Use path from utils
                        made_changes = True
                        logger.info(f"Updated stage 3 status for video ID: {video_id}")

                    # Check for and create transcript processing entry if needed
                    tp = db_session.query(db.TranscriptProcessing).filter(db.TranscriptProcessing.video_id == video.id).first()
                    if not tp:
                        # Read the transcript to get the word count
                        with open(local_transcript_path, 'r') as f:
                            raw_text = f.read()
                        word_count = len(raw_text.split())

                        new_transcript_processing = db.TranscriptProcessing(
                            video_id=video.id,
                            raw_transcript_path=paths["raw_transcript_path"], # <--- Use path from utils
                            starting_word_count=word_count,
                            status="raw_transcript_received"
                        )
                        db_session.add(new_transcript_processing)
                        
                        # Also update stage 4 status on the video
                        video.stage_4_status = "completed"
                        made_changes = True
                        logger.info(f"Created transcript_processing entry and updated stage 4 status for video ID: {video_id}")

                    if made_changes:
                        db_session.commit()

    finally:
        db_session.close()

if __name__ == "__main__":
    check_remote_status_and_fetch_completed()
