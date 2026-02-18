import logging
from pathlib import Path
from rich import box
import random

logger = logging.getLogger(__name__)
logger.debug("config/config.py module loaded. Initializing configuration parameters.")

# Define the absolute path to the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
logger.debug("PROJECT_ROOT: %s", PROJECT_ROOT)

# Define other configurations relative to the project root
DATABASE_PATH = PROJECT_ROOT / "project_database.db"
logger.debug("DATABASE_PATH: %s", DATABASE_PATH)
FASTAPI_URL = "http://192.168.68.66:5000"  # make sure to add a / before endpoints
logger.debug("FASTAPI_URL: %s", FASTAPI_URL)

# Rich library box style options
box_options = [
    box.SQUARE,
    box.ROUNDED,
    box.MINIMAL,
    box.MINIMAL_DOUBLE_HEAD,
    box.DOUBLE,  # thick, heavy borders
    box.HEAVY,  # very bold borders
]
BOX_STYLE = box.ROUNDED
logger.debug("BOX_STYLE set to ROUNDED.")


def build_job_directory_path(job_ulid: str, job_id: int) -> str:
    """
    Constructs the path for a job's directory and ensures it exists.
    """
    logger.debug(f"Building job directory path for ULID: {job_ulid}, ID: {job_id}")
    job_dir = PROJECT_ROOT / "jobs" / f"{job_ulid}_{job_id}"
    job_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Job directory created/ensured: {job_dir}")
    return str(job_dir)


# standard file names for the jobs
VIDEO_NAME = "video.mp4"
FULL_MP3_NAME = "audio_full.mp3"
MP3_SEGMENT_NAME = "audio_segment.mp3"
WHISPER_TRANSCRIPT_NAME = "whisper_transcript.txt"
FORMATED_TRANSCRIPT_NAME = "formatted_transcript.txt"
METADATA_FILE_NAME = "metadata.json"
PARAGRAPHS_FILE_NAME = "paragraphs.json"
FINAL_DOCUMENT_NAME = "finsihed-document.txt"

METADATA_CATEGORIES = [
    "title",
    "thesis",
    "summary",
    "outline",
    "tone",
    "main_text",
]  # New constant
logger.debug("METADATA_CATEGORIES defined: %s", METADATA_CATEGORIES)

WHISPER_MODEL = "large"
logger.debug("WHISPER_MODEL set to '%s'", WHISPER_MODEL)

_spinner_styles = [
    "aesthetic"
    "arc"
    "arrow"
    "arrow2"
    "arrow3"
    "balloon"
    "balloon2"
    "betaWave"
    "bounce"
    "bouncingBall"
    "bouncingBar"
    "boxBounce"
    "boxBounce2"
    "christmas"
    "circle"
    "circleHalves"
    "circleQuarters"
    "clock"
    "dots"
    "dots10"
    "dots11"
    "dots12"
    "dots2"
    "dots3"
    "dots4"
    "dots5"
    "dots6"
    "dots7"
    "dots8"
    "dots8Bit"
    "dots9"
    "dqpb"
    "earth"
    "flip"
    "grenade"
    "growHorizontal"
    "growVertical"
    "hamburger"
    "hearts"
    "layer"
    "line"
    "line2"
    "material"
    "monkey"
    "moon"
    "noise"
    "pipe"
    "point"
    "pong"
    "runner"
    "shark"
    "simpleDots"
    "simpleDotsScrolling"
    "smiley"
    "squareCorners"
    "squish"
    "star"
    "star2"
    "toggle"
    "toggle10"
    "toggle11"
    "toggle12"
    "toggle13"
    "toggle2"
    "toggle3"
    "toggle4"
    "toggle5"
    "toggle6"
    "toggle7"
    "toggle8"
    "toggle9"
    "triangle"
    "weather"
]
_josh_favorite_spinners = [
    "aesthetic",
    "toggle7",
    "toggle10",
    "dots10",
    "dots12",
    "growVertical",
    "pong",
    "bouncingBall",
]
SPINNER = "dots12"
logger.debug("Default SPINNER set to '%s'", SPINNER)


def select_random_spinner():
    SPINNER_STYLE = random.choice(_josh_favorite_spinners)
    logger.debug("Random spinner selected: '%s'", SPINNER_STYLE)
