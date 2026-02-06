import yt_dlp
import csv
import re
from pathlib import Path
from db import SessionLocal, Video
from logger import setup_logger

logger = setup_logger(__name__)


def extract_yt_id(url):
    """Extracts the YouTube video ID from a URL using regex."""
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else None


def get_video_metadata(url):
    """
    Fetches video metadata using yt-dlp without downloading the video.

    Args:
        url (str): The URL of the YouTube video.

    Returns:
        dict: A dictionary containing the video's metadata.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(url, download=False)

            video_details = {
                "yt_id": info_dict.get("id"),
                "title": info_dict.get("title"),
                "uploader": info_dict.get("uploader"),
                "channel_id": info_dict.get("channel_id"),
                "channel_url": info_dict.get("channel_url"),
                "upload_date": info_dict.get("upload_date"),
                "duration": info_dict.get("duration"),
                "webpage_url": info_dict.get("webpage_url"),
                "description": info_dict.get("description"),
                "thumbnail": info_dict.get("thumbnail"),
                "was_live": info_dict.get("was_live"),
                "live_status": info_dict.get("live_status"),
            }
            return video_details

        except yt_dlp.utils.DownloadError as e:
            logger.error(f"Error fetching metadata for {url}: {e}")
            return {}


def process_csv():
    """
    Processes a CSV file containing YouTube URLs and returns a list of dictionaries.
    """
    url_data = []  # list of dicts to hold processed data

    csv_path = Path(__file__).parent / "video_urls.csv"
    if not csv_path.exists():
        logger.error(f"CSV file not found at {csv_path}")
        return []

    with open(csv_path, mode="r", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        data_dict = list(reader)

    for d in data_dict:
        try:
            start_time = (
                int(d.get("start_hour", 0)) * 3600
                + int(d.get("start_min", 0)) * 60
                + int(d.get("start_sec", 0))
            )
            end_time = (
                int(d.get("end_hour", 0)) * 3600
                + int(d.get("end_min", 0)) * 60
                + int(d.get("end_sec", 0))
            )
            url_data.append(
                {
                    "url": d.get("url"),
                    "start_time": start_time,
                    "end_time": end_time,
                }
            )
        except (ValueError, TypeError) as e:
            logger.warning(f"Skipping row due to invalid time value: {d} - Error: {e}")

    return url_data


def process_video_links():
    logger.info("Starting video processing...")
    video_data = process_csv()
    if not video_data:
        logger.warning("No videos found in CSV file. Exiting.")
        return

    db = SessionLocal()
    try:
        existing_yt_ids = {video.yt_id for video in db.query(Video.yt_id).all()}
        logger.info(f"Found {len(existing_yt_ids)} existing videos in the database.")

        new_videos_to_process = []
        for row in video_data:
            url = row.get("url")
            if not url:
                continue
            yt_id = extract_yt_id(url)
            if yt_id and yt_id not in existing_yt_ids:
                new_videos_to_process.append(row)
            elif yt_id:
                logger.debug(f"Skipping already existing video: {url}")

        if not new_videos_to_process:
            logger.info("No new videos to process.")
            return

        logger.info(f"Found {len(new_videos_to_process)} new videos to process.")
        for i, row in enumerate(new_videos_to_process, 1):
            logger.info(
                f"--- Processing new video {i} of {len(new_videos_to_process)} ---"
            )
            url = row.get("url")
            logger.info(f"URL: {url}")

            logger.info("Fetching video metadata...")
            video_metadata = get_video_metadata(url)
            if not video_metadata or not video_metadata.get("yt_id"):
                logger.warning("Could not fetch metadata. Skipping.")
                continue

            new_video = Video(
                **video_metadata,
                start_time=row.get("start_time"),
                end_time=row.get("end_time"),
                stage_1_status="completed",
            )

            db.add(new_video)
            db.commit()
            existing_yt_ids.add(
                new_video.yt_id
            )  # Add to set to avoid re-processing in same run
            logger.info(
                f"Successfully added video '{new_video.title}' to the database."
            )

    finally:
        db.close()
    logger.info("--- Video processing complete. ---")
