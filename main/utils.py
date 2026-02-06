from pathlib import Path
from db import SessionLocal, Video, TranscriptProcessing
import os
import re
from logger import setup_logger

logger = setup_logger(__name__)


def _get_video_duration_str(db_session, video_id: int) -> str:
    """
    Fetches the video duration from the database and formats it as HH:MM:SS.
    """
    try:
        video = db_session.query(Video).filter(Video.id == video_id).first()
        if not video or video.duration is None:
            logger.warning(f"Could not find video or duration for video_id {video_id}.")
            return None

        total_seconds = int(video.duration)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        return f"{hours:02}:{minutes:02}:{seconds:02}"
    except Exception as e:
        logger.error(
            f"Error fetching video duration for video_id {video_id}: {e}", exc_info=True
        )
        return None


def get_video_paths(video: Video):
    """
    Generates a dictionary of all relevant file paths for a given video object.
    """
    if not video or not video.id or not video.yt_id:
        return None

    DOWNLOADS_DIR = Path(__file__).parent / "downloads"
    video_dir_name = f"{video.id}_{video.yt_id}"
    video_dir = DOWNLOADS_DIR / video_dir_name

    base_filename = f"{video.yt_id}_trimmed"

    return {
        "video_dir": str(video_dir),
        "download_path": str(video_dir),
        "mp3_path": str(video_dir / f"{base_filename}.mp3"),
        "transcript_path": str(
            video_dir / f"{base_filename}.txt"
        ),  # This path is for the initial raw transcript from whisper
        "raw_transcript_path": str(
            video_dir / f"{base_filename}.txt"
        ),  # This path is for the initial raw transcript for TranscriptProcessing
        "initial_cleaning_path": str(video_dir / f"{base_filename}.initial.txt"),
        "secondary_cleaning_path": str(video_dir / f"{base_filename}.secondary.txt"),
        "final_pass_path": str(video_dir / f"{base_filename}.final.txt"),
        "metadata_path": str(video_dir / f"{base_filename}.meta.txt"),
        "book_ready_path": str(video_dir / f"{base_filename}.book.txt"),
    }


def get_video_from_path(file_path: str, db_session):
    """
    Extracts the video ID from a file path and fetches the video object.
    """
    # Regex to find N_ytid where N is the video ID
    match = re.search(r"/(\d+)_[^/]+/", file_path)
    if match:
        video_id = int(match.group(1))
        return db_session.query(Video).filter_by(id=video_id).first()
    return None


def adjust_dir_names():
    """
    Adjusts directory names in the downloads folder to include video IDs
    AND updates the file paths in the database to match.
    This is a migration script.
    """
    db = SessionLocal()
    DOWNLOADS_DIR = Path(__file__).parent / "downloads"
    print(f"Scanning directory: {DOWNLOADS_DIR}")

    count_renamed = 0
    count_video_paths_updated = 0
    count_transcript_paths_updated = 0

    for video in db.query(Video).all():
        # Generate the correct new paths
        paths = get_video_paths(video)
        if not paths:
            continue

        new_dir = Path(paths["video_dir"])

        # Find the old directory - it could be just the yt_id or something else
        # This iterates through existing directories in 'downloads' to find the one
        # that matches the video's yt_id but isn't already the new_dir format.
        old_dir = None
        for item in DOWNLOADS_DIR.iterdir():
            if item.is_dir() and video.yt_id in str(item):
                # Ensure we are not picking up the already correctly named directory
                # and that it's not a directory that just happens to contain the yt_id
                # but isn't directly related to *this* video's old naming convention.
                # A common old naming convention would be just the yt_id itself.
                if item.name == video.yt_id:  # Direct old name match
                    old_dir = item
                    break
                # Or if it's already the new format, we don't need to rename
                if item.name == new_dir.name:
                    old_dir = None  # Already correct, no rename needed
                    break

        # 1. RENAME DIRECTORY ON DISK
        if old_dir and old_dir.exists() and not new_dir.exists():
            try:
                old_dir.rename(new_dir)
                print(f"Directory Renamed: {old_dir.name} -> {new_dir.name}")
                count_renamed += 1
            except OSError as e:
                print(f"Error renaming {old_dir}: {e}")
                continue
        elif new_dir.exists() and not old_dir:
            # Directory already has the new name, or was renamed previously.
            # No disk rename needed for this video.
            pass
        elif old_dir and new_dir.exists() and old_dir.exists():
            # Both exist, this should ideally not happen or means a conflict.
            # For now, we'll assume the new_dir is the correct one if it exists.
            print(
                f"Warning: Both {old_dir.name} and {new_dir.name} exist for video {video.id}. Proceeding with new_dir."
            )

        # 2. UPDATE VIDEO DATABASE PATHS
        video_paths_changed = False
        if video.download_path != paths["download_path"]:
            video.download_path = paths["download_path"]
            video_paths_changed = True

        if video.mp3_path != paths["mp3_path"]:
            video.mp3_path = paths["mp3_path"]
            video_paths_changed = True

        if video.transcript_path != paths["transcript_path"]:
            video.transcript_path = paths["transcript_path"]
            video_paths_changed = True

        if video_paths_changed:
            count_video_paths_updated += 1

        # 3. UPDATE TRANSCRIPTPROCESSING DATABASE PATHS
        transcript_processing_entry = (
            db.query(TranscriptProcessing).filter_by(video_id=video.id).first()
        )
        if transcript_processing_entry:
            transcript_paths_changed = False

            if (
                transcript_processing_entry.raw_transcript_path
                != paths["raw_transcript_path"]
            ):
                transcript_processing_entry.raw_transcript_path = paths[
                    "raw_transcript_path"
                ]
                transcript_paths_changed = True

            if (
                transcript_processing_entry.initial_cleaning_path
                != paths["initial_cleaning_path"]
            ):
                transcript_processing_entry.initial_cleaning_path = paths[
                    "initial_cleaning_path"
                ]
                transcript_paths_changed = True

            if (
                transcript_processing_entry.secondary_cleaning_path
                != paths["secondary_cleaning_path"]
            ):
                transcript_processing_entry.secondary_cleaning_path = paths[
                    "secondary_cleaning_path"
                ]
                transcript_paths_changed = True

            if transcript_processing_entry.final_pass_path != paths["final_pass_path"]:
                transcript_processing_entry.final_pass_path = paths["final_pass_path"]
                transcript_paths_changed = True

            if transcript_processing_entry.metadata_path != paths["metadata_path"]:
                transcript_processing_entry.metadata_path = paths["metadata_path"]
                transcript_paths_changed = True

            if transcript_processing_entry.book_ready_path != paths["book_ready_path"]:
                transcript_processing_entry.book_ready_path = paths["book_ready_path"]
                transcript_paths_changed = True

            if transcript_paths_changed:
                count_transcript_paths_updated += 1

    # 4. COMMIT CHANGES
    try:
        db.commit()
        print(
            f"Success! Renamed {count_renamed} folders, updated {count_video_paths_updated} video records, and {count_transcript_paths_updated} transcript processing records."
        )
    except Exception as e:
        db.rollback()
        print(f"Database Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    adjust_dir_names()
