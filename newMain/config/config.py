from pathlib import Path
from rich import box

# Define the absolute path to the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Define other configurations relative to the project root
DATABASE_PATH = PROJECT_ROOT / "project_database.db"
FASTAPI_URL="http://192.168.68.66:5000"  # make sure to add a / before endpoints

BOX_STYLE = box.ROUNDED

def build_job_directory_path(job_ulid: str, job_id: int) -> str:
    """
    Constructs the path for a job's directory and ensures it exists.
    """
    job_dir = PROJECT_ROOT / "jobs" / f"{job_ulid}_{job_id}"
    job_dir.mkdir(parents=True, exist_ok=True)
    return str(job_dir)

"""
rich box options:
box_options = [
    box.SQUARE,
    box.ROUNDED,
    box.MINIMAL,
    box.MINIMAL_DOUBLE_HEAD,
    box.DOUBLE,          # thick, heavy borders
    box.HEAVY,           # very bold borders
]
"""

# standard file names for the jobs
VIDEO_NAME = 'video.mp4'
FULL_MP3_NAME = 'audio_full.mp3'
MP3_SEGMENT_NAME = 'audio_segment.mp3'
WHISPER_TRANSCRIPT_NAME = 'whisper_transcript.txt'
FORMATED_TRANSCRIPT_NAME = 'formated_transcript.txt'

WHISPER_MODEL = 'large'