
import json
from pathlib import Path
from desktop_connection_utility import sftp_put, run_remote_cmd

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
        print(f"Uploading {LOCAL_SCRIPT_PATH.name} to {REMOTE_SCRIPT_PATH}...")
        sftp_put(str(LOCAL_SCRIPT_PATH), REMOTE_SCRIPT_PATH)

        # 2. Execute the script on the remote machine
        print("Executing remote script to check database status...")
        remote_cmd = f"cd {REMOTE_PROJECT_DIR} && source venvFiles39/bin/activate && python3 {REMOTE_SCRIPT_PATH}"
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

        total_files = len(remote_statuses)
        print(f"\n--- Remote Database Status Summary ---")
        print(f"Total files in database: {total_files}")

        status_counts = {}
        for item in remote_statuses:
            status = item.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

        for status, count in status_counts.items():
            print(f"- {status.capitalize()}: {count}")

        print("\n--- Detailed File Status ---")
        for item in sorted(remote_statuses, key=lambda x: x.get('mp3_id', 0)):
            mp3_id = item.get('mp3_id', 'N/A')
            status = item.get('status', 'N/A')
            processing_time = item.get('processing_time_seconds', 'N/A')
            status_char = get_status_char(status)
            
            print(f"  ID: {mp3_id:<3} [{status_char}] - {status} (Processing Time: {processing_time}s)")
        print("-----------------------------")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    display_remote_db_info()
