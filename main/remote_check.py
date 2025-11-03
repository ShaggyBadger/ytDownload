
import json
import sqlite3
from pathlib import Path

# Define paths relative to the script's execution directory on the remote machine
DB_PATH = "/home/alexander/pyProjects/sermonTranscriber/main/sermons.db"
COMPLETED_TRANSCRIPTIONS_DIR = "/home/alexander/pyProjects/sermonTranscriber/main/completed_transcriptions"

def create_table_if_not_exists(conn):
    """Creates the 'files' table if it doesn't exist."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY,
            mp3_id INTEGER UNIQUE,
            mp3_path TEXT,
            transcript_path TEXT,
            status TEXT DEFAULT 'pending',
            processing_time_seconds INTEGER
        )
    """)
    conn.commit()

def check_remote_db():
    """
    Connects to the remote SQLite database and retrieves the status of all files.
    Also checks for the existence of the transcript file.
    Returns a JSON string with the results.
    """
    results = []
    try:
        conn = sqlite3.connect(DB_PATH)
        create_table_if_not_exists(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT id, mp3_id, mp3_path, transcript_path, status, processing_time_seconds FROM files")
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            id, mp3_id, mp3_path, transcript_path, status, processing_time_seconds = row
            transcript_exists = False
            if transcript_path and Path(transcript_path).exists():
                transcript_exists = True
            
            results.append({
                "id": id,
                "mp3_id": mp3_id,
                "mp3_path": mp3_path,
                "transcript_path": transcript_path,
                "status": status,
                "processing_time_seconds": processing_time_seconds,
                "transcript_exists": transcript_exists
            })

    except Exception as e:
        results.append({"error": str(e)})

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    check_remote_db()
