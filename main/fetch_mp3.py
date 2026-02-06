import yt_dlp
from db import SessionLocal, Video
from utils import get_video_paths
from pydub import AudioSegment
from pathlib import Path
from logger import setup_logger
import time

logger = setup_logger(__name__)


def select_videos_to_process():
    """
    Fetches and displays videos pending MP3 processing,
    and prompts the user to select which ones to process.
    """
    db = SessionLocal()
    videos_pending = (
        db.query(Video)
        .filter(
            Video.stage_1_status == "completed", Video.stage_2_status != "completed"
        )
        .all()
    )
    db.close()

    if not videos_pending:
        logger.info("No videos are currently pending for MP3 processing.")
        return []

    logger.info(
        "\n--- Videos Pending MP3 Processing ---\n"
        + "\n".join(
            [f"{i}: {video.title}" for i, video in enumerate(videos_pending, 1)]
        )
        + "\nall: Process all listed videos"
        + "\n------------------------------------"
    )

    while True:
        user_input = input("Enter the number of the video to process (or 'all'): ")
        logger.info(f"User input: {user_input}")

        if user_input.lower() == "all":
            return videos_pending

        try:
            selected_index = int(user_input) - 1
            if 0 <= selected_index < len(videos_pending):
                # Return a list containing the single selected video
                return [videos_pending[selected_index]]
            else:
                logger.warning(
                    f"Invalid number. Please enter a number between 1 and {len(videos_pending)}."
                )
        except ValueError:
            logger.warning("Invalid input. Please enter a number or 'all'.")


def process_selected_videos(videos_to_process):
    """
    Downloads and trims MP3 audio for the selected video objects.
    """
    if not videos_to_process:
        logger.info("No videos selected for processing.")
        return

    db = SessionLocal()

    # DOWNLOADS_DIR is now derived from get_video_paths, but we still need its base path
    BASE_DOWNLOADS_DIR = Path(__file__).parent / "downloads"
    BASE_DOWNLOADS_DIR.mkdir(exist_ok=True)

    for video in videos_to_process:
        logger.info(f"--- Starting processing for: {video.title} ---")

        paths = get_video_paths(video)
        if not paths:
            logger.error(f"Could not get paths for video {video.id} - {video.yt_id}")
            continue

        video_dir = Path(paths["video_dir"])
        video_dir.mkdir(exist_ok=True)

        full_audio_path = (
            video_dir / f"{video.yt_id}_full.mp3"
        )  # This is a temporary file, not stored in DB directly
        trimmed_audio_path = Path(paths["mp3_path"])

        try:
            # --- HOOKS for yt-dlp ---
            def progress_hook(d):
                if d["status"] == "downloading":
                    percent_str = d.get("_percent_str", "0.0%").strip()
                    speed_str = d.get("_speed_str", "0.0B/s").strip()
                    eta_str = d.get("_eta_str", "00:00").strip()
                    logger.info(
                        f"Downloading: {percent_str} | {speed_str} | ETA: {eta_str}"
                    )
                if d["status"] == "finished":
                    logger.info("Download complete.")

            def postprocessor_hook(d):
                if d["status"] == "started":
                    logger.info(f"Post-processing: {d['postprocessor']}...")
                if d["status"] == "finished":
                    logger.info("Post-processing complete. Pausing for 2 seconds...")
                    time.sleep(2)

            # ------------------------

            # Download
            ydl_opts = {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
                "outtmpl": str(full_audio_path).replace(
                    ".mp3", ""
                ),  # yt-dlp adds the extension
                "keepvideo": False,
                "progress_hooks": [progress_hook],
                "postprocessor_hooks": [postprocessor_hook],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download([video.webpage_url])
                except Exception as e:
                    logger.error("yt-dlp failed. Re-running with -v for full debug...")

                    # Run shell-level yt-dlp debug to get full FFmpeg logs
                    import subprocess

                    dbg_cmd = [
                        "yt-dlp",
                        "-v",
                        video.webpage_url,
                        "-o",
                        str(full_audio_path).replace(".mp3", ""),
                    ]
                    dbg = subprocess.run(dbg_cmd, capture_output=True, text=True)
                    logger.debug(f"YT-DLP DEBUG STDOUT: {dbg.stdout}")
                    logger.debug(f"YT-DLP DEBUG STDERR: {dbg.stderr}")

                    raise

            # Trim
            logger.info("Trimming audio...")
            audio = AudioSegment.from_file(full_audio_path)
            start_ms = video.start_time * 1000
            end_ms = video.end_time * 1000
            trimmed_audio = audio[start_ms:end_ms]
            trimmed_audio.export(trimmed_audio_path, format="mp3")

            # Update DB
            db_video = db.query(Video).filter(Video.id == video.id).first()
            if db_video:
                db_video.stage_2_status = "completed"
                db_video.download_path = paths[
                    "download_path"
                ]  # Path to the video's directory
                db_video.mp3_path = paths["mp3_path"]  # Path to the trimmed MP3
                db.commit()
                logger.info(f"Successfully processed and saved to {trimmed_audio_path}")

        except Exception as e:
            logger.error(f"An error occurred while processing {video.title}: {e}")
            db.rollback()  # Ensure the session is clean before updating status
            db_video = db.query(Video).filter(Video.id == video.id).first()
            if db_video:
                db_video.stage_2_status = "failed"
                db_video.error_message = str(e)
                db.commit()

    db.close()


if __name__ == "__main__":
    selected_videos = select_videos_to_process()
    process_selected_videos(selected_videos)
