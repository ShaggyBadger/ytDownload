import json
from pathlib import Path
from desktop_connection_utility import sftp_put, run_remote_cmd
from logger import setup_logger

logger = setup_logger(__name__)

# Define remote paths
REMOTE_PROJECT_DIR = "/home/alexander/pyProjects/sermonTranscriber"
REMOTE_SCRIPT_PATH = f"{REMOTE_PROJECT_DIR}/remote_check.py"
LOCAL_SCRIPT_PATH = Path(__file__).parent / "remote_check.py"

def get_status_char(status):
    """Returns a single character representation of a status."""
    if not status:
        return ' '
    return status[0].upper()

def display_remote_db_info():
    """
    Connects to the remote database and displays a summary of file statuses.
    """
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

        total_files = len(remote_statuses)
        logger.info("--- Remote Database Status Summary ---")
        logger.info(f"Total files in database: {total_files}")

        status_counts = {}
        for item in remote_statuses:
            status = item.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

        for status, count in status_counts.items():
            logger.info(f"- {status.capitalize()}: {count}")

        logger.info("--- Detailed File Status ---")
        for item in sorted(remote_statuses, key=lambda x: x.get('mp3_id', 0)):
            mp3_id = item.get('mp3_id', 'N/A')
            status = item.get('status', 'N/A')
            processing_time = item.get('processing_time_seconds', 'N/A')
            status_char = get_status_char(status)
            
            logger.info(f"  ID: {mp3_id:<3} [{status_char}] - {status} (Processing Time: {processing_time}s)")
        logger.info("-----------------------------")

    except Exception as e:
        logger.error(f"An error occurred: {e}")

if __name__ == '__main__':
    display_remote_db_info()
