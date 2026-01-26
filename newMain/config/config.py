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
METADATA_FILE_NAME = 'metadata.json'

WHISPER_MODEL = 'large'

spinner_styles = [
    'aesthetic'
    'arc'
    'arrow'
    'arrow2'
    'arrow3'
    'balloon'
    'balloon2'
    'betaWave'
    'bounce'
    'bouncingBall'
    'bouncingBar'
    'boxBounce'
    'boxBounce2'
    'christmas'
    'circle'
    'circleHalves'
    'circleQuarters'
    'clock'
    'dots'
    'dots10'
    'dots11'
    'dots12'
    'dots2'
    'dots3'
    'dots4'
    'dots5'
    'dots6'
    'dots7'
    'dots8'
    'dots8Bit'
    'dots9'
    'dqpb'
    'earth'
    'flip'
    'grenade'
    'growHorizontal'
    'growVertical'
    'hamburger'
    'hearts'
    'layer'
    'line'
    'line2'
    'material'
    'monkey'
    'moon'
    'noise'
    'pipe'
    'point'
    'pong'
    'runner'
    'shark'
    'simpleDots'
    'simpleDotsScrolling'
    'smiley'
    'squareCorners'
    'squish'
    'star'
    'star2'
    'toggle'
    'toggle10'
    'toggle11'
    'toggle12'
    'toggle13'
    'toggle2'
    'toggle3'
    'toggle4'
    'toggle5'
    'toggle6'
    'toggle7'
    'toggle8'
    'toggle9'
    'triangle'
    'weather'
]
SPINNER_STYLE = 'aesthetic'