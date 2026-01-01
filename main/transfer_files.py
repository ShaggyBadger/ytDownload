import json
from pathlib import Path
import db
from desktop_connection_utility import sftp_put, run_remote_cmd, create_remote_dir_if_not_exists
from logger import setup_logger

logger = setup_logger(__name__)

# Define remote paths
REMOTE_PROJECT_DIR = "/home/alexander/pyProjects/sermonTranscriber"
REMOTE_MAIN_DIR = f"{REMOTE_PROJECT_DIR}/main"
REMOTE_AUDIO_DIR = f"{REMOTE_MAIN_DIR}/audio_files"
REMOTE_JSON_PATH = f"{REMOTE_MAIN_DIR}/new_files.json"

def prepare_and_transfer_files():
    """
    Prepares a list of MP3 files and a corresponding JSON file to be
    transferred to the remote desktop for transcription.
    """
    db_session = db.SessionLocal()
    local_json_path = None
    try:
        # 1. Get videos ready for transcription
        videos_to_transcribe = db_session.query(db.Video).filter(
            db.Video.stage_2_status == "completed",
            db.Video.stage_3_status == "pending"
        ).all()

        if not videos_to_transcribe:
            logger.info("No new videos to transcribe.")
            return

        logger.info(f"Found {len(videos_to_transcribe)} videos to transfer for transcription.")

        # 2. Prepare the JSON data
        json_data = []
        for video in videos_to_transcribe:
            json_data.append({
                "mp3Id": video.id,
                "mp3Name": Path(video.mp3_path).name
            })

        # Create a temporary local JSON file
        local_json_path = Path(__file__).parent / "new_files.json"
        with open(local_json_path, "w") as f:
            json.dump(json_data, f, indent=2)

        # 3. Transfer the files
        logger.info("Transferring files to the remote desktop...")

        # Create remote audio directory if it doesn't exist
        create_remote_dir_if_not_exists(REMOTE_AUDIO_DIR)

        # Transfer the JSON file
        sftp_put(str(local_json_path), REMOTE_JSON_PATH)
        logger.info(f"Transferred {local_json_path.name} to {REMOTE_JSON_PATH}")

        # Transfer the MP3 files
        for video in videos_to_transcribe:
            local_mp3_path = Path(video.mp3_path)
            remote_mp3_path = f"{REMOTE_AUDIO_DIR}/{local_mp3_path.name}"
            sftp_put(str(local_mp3_path), remote_mp3_path)
            logger.info(f"Transferred {local_mp3_path.name} to {remote_mp3_path}")

        # 4. Update the database
        for video in videos_to_transcribe:
            video.stage_3_status = "processing"
        db_session.commit()


        logger.info("File transfer and remote processing initiated successfully.")

    finally:
        db_session.close()
        # Clean up the temporary JSON file
        if local_json_path and local_json_path.exists():
            local_json_path.unlink()

if __name__ == "__main__":
    prepare_and_transfer_files()


def transfer_all_mp3_info_json():
    """
    Prepares and transfers a JSON file containing mp3Id and mp3Name for all
    videos that have completed stage 2 (MP3 download and trim).
    """
    db_session = db.SessionLocal()
    local_json_path = None
    try:
        # 1. Get all videos that have completed stage 2
        all_completed_mp3_videos = db_session.query(db.Video).filter(
            db.Video.stage_2_status == "completed"
        ).all()

        if not all_completed_mp3_videos:
            logger.info("No videos with completed MP3s found in the database.")
            return

        logger.info(f"Found {len(all_completed_mp3_videos)} videos with completed MP3s.")

        # 2. Prepare the JSON data with mp3Id and mp3Name
        json_data = []
        for video in all_completed_mp3_videos:
            json_data.append({
                "mp3Id": video.id,
                "mp3Name": Path(video.mp3_path).name
            })

        # Create a temporary local JSON file
        local_json_path = Path(__file__).parent / "all_files.json"
        with open(local_json_path, "w") as f:
            json.dump(json_data, f, indent=2)

        # 3. Transfer the JSON file
        logger.info("Transferring all MP3 info JSON to the remote desktop...")
        # Use the same remote path as the standard transfer
        sftp_put(str(local_json_path), REMOTE_JSON_PATH)
        logger.info(f"Transferred {local_json_path.name} to {REMOTE_JSON_PATH}")

        logger.info("All MP3 info JSON transfer complete.")

    finally:
        db_session.close()
        # Clean up the temporary JSON file
        if local_json_path and local_json_path.exists():
            local_json_path.unlink()
