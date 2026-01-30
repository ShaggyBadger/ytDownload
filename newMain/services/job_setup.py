"""
This module provides services for ingesting video information into the database.
It defines functions to add new video entries and manage database sessions.
"""

import logging
import re
from datetime import datetime, timedelta
import yt_dlp

from rich.console import Console
from rich.prompt import Prompt

from database.session_manager import get_session
from database.models import VideoInfo, JobInfo, JobStage, StageState, STAGE_ORDER
from config.config import build_job_directory_path

logger = logging.getLogger(__name__)


class IngestLink:
    def __init__(self, data_packet):
        self.link = data_packet.get("link")
        self.start_seconds = data_packet.get("start_time")  # in seconds
        self.end_seconds = data_packet.get("end_time")  # in seconds
        self.console = Console()
        logger.debug(
            f"IngestLink initialized for link: {self.link}, start: {self.start_seconds}s, end: {self.end_seconds}s"
        )

    def _extract_yt_id(self, url):
        """
        Extracts the YouTube video ID from a given URL.
        Supports standard, shortened, and embed URLs.
        """
        if not url:
            logger.warning("Attempted to extract YouTube ID from a null or empty URL.")
            return None
        logger.debug(f"Attempting to extract YouTube ID from URL: {url}")

        youtube_regex = (
            r"(?:https?://)?(?:www\.)?"
            r"(?:youtube\.com/(?:watch\?v=|embed/|v/)|youtu\.be/)"
            r"([a-zA-Z0-9_-]{11})"
        )
        match = re.search(youtube_regex, url)
        if match:
            yt_id = match.group(1)
            logger.debug(f"Successfully extracted YouTube ID: {yt_id}")
            return yt_id

        logger.warning(f"Could not extract a valid YouTube ID from URL: {url}")
        return None

    def _get_video_metadata(self, url):
        """
        Fetches video metadata using yt-dlp without downloading the video.
        """
        logger.info(f"Fetching metadata with yt-dlp for URL: {url}")
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "simulate": True,
            "force_generic_extractor": False,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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
                logger.debug(
                    f"Successfully fetched metadata for yt_id: {video_details.get('yt_id')}"
                )
                return video_details
        except yt_dlp.utils.DownloadError:
            logger.error(
                f"yt-dlp failed to fetch metadata for URL: {url}", exc_info=True
            )
            return {}
        except Exception:
            logger.critical(
                f"An unexpected error occurred during yt-dlp metadata extraction for {url}",
                exc_info=True,
            )
            return {}

    def ingest_into_db(self):
        """
        Ingests the video link information and job details into the database.
        Returns the new JobInfo object on success, None on failure.
        """
        logger.info(f"Starting database ingestion for link: {self.link}")
        yt_id = self._extract_yt_id(self.link)
        if not yt_id:
            logger.error(
                f"Could not ingest link because YouTube ID extraction failed for: {self.link}"
            )
            return None

        try:
            with get_session() as session:
                # Find or create VideoInfo entry
                logger.debug(f"Querying for existing VideoInfo with yt_id: {yt_id}")
                video_info = session.query(VideoInfo).filter_by(yt_id=yt_id).first()
                if not video_info:
                    logger.info(
                        f"No existing VideoInfo found for yt_id: {yt_id}. Fetching new metadata."
                    )
                    metadata = self._get_video_metadata(self.link)

                    if not metadata:
                        logger.error(
                            f"Failed to fetch metadata for {self.link}. Aborting ingestion."
                        )
                        return None

                    video_info = VideoInfo(**metadata)
                    session.add(video_info)
                    session.flush()  # Ensure video_info gets an ID
                    logger.info(
                        f"New VideoInfo created with ID: {video_info.id} for yt_id: {yt_id}"
                    )
                else:
                    logger.info(
                        f"Found existing VideoInfo with ID: {video_info.id} for yt_id: {yt_id}"
                    )

                # Create JobInfo entry
                new_job = JobInfo(
                    video_id=video_info.id,
                    audio_start_time=self.start_seconds,
                    audio_end_time=self.end_seconds,
                )
                session.add(new_job)
                session.flush()  # Ensure new_job gets an ID
                logger.info(
                    f"New JobInfo created with temporary ID: {new_job.id} and ULID: {new_job.job_ulid}"
                )

                new_job.job_directory = build_job_directory_path(
                    new_job.job_ulid, new_job.id
                )
                logger.info(
                    f"Set job directory for Job ID {new_job.id} to: {new_job.job_directory}"
                )

                # Create JobStage entries for the new job
                logger.debug(
                    f"Creating {len(STAGE_ORDER)} JobStage entries for Job ID {new_job.id}"
                )
                for stage_name in STAGE_ORDER:
                    job_stage = JobStage(
                        job_id=new_job.id,
                        stage_name=stage_name,
                        state=StageState.pending,
                    )
                    session.add(job_stage)

                session.commit()
                logger.info(
                    f"Successfully committed Job ID {new_job.id} and its {len(STAGE_ORDER)} stages to the database."
                )
                self.console.print(
                    f"[bold green]Successfully ingested job for {self.link} (Job ID: {new_job.id})[/bold green]"
                )
                return new_job
        except Exception:
            logger.critical(
                "A critical error occurred during the database transaction.",
                exc_info=True,
            )
            self.console.print(
                "[bold red]A critical error occurred during ingestion. Check the logs for details.[/bold red]"
            )
            return None


class ManualJobSetup:
    """Handles the setup of a single job provided manually."""

    def __init__(self):
        self.console = Console()
        logger.debug("ManualJobSetup initialized.")

    def run(self):
        """The main execution method for the manual job setup flow."""
        self.console.clear()
        self.console.rule("[bold yellow]Service: Manual Job Setup[/bold yellow]")
        logger.info("Starting manual job setup flow.")

        solicit_input = True
        while solicit_input:
            link = Prompt.ask("Enter YouTube URL")
            start_time_str = Prompt.ask(
                "Enter start time (HH:MM:SS, MM:SS, or SS)", default="0"
            )
            end_time_str = Prompt.ask(
                "Enter end time (HH:MM:SS, MM:SS, or SS)", default="0"
            )
            logger.debug(
                f"User input received: link='{link}', start_time='{start_time_str}', end_time='{end_time_str}'"
            )

            start_seconds = self._parse_time_to_seconds(start_time_str)
            end_seconds = self._parse_time_to_seconds(end_time_str)

            if start_seconds is None:
                self.console.print(
                    f"[red]Error: Invalid start time format: '{start_time_str}'. Please use HH:MM:SS, MM:SS, or SS.[/red]"
                )
                logger.warning(
                    f"Invalid start time format provided by user: '{start_time_str}'"
                )
                continue

            if end_seconds is None:
                self.console.print(
                    f"[red]Error: Invalid end time format: '{end_time_str}'. Please use HH:MM:SS, MM:SS, or SS.[/red]"
                )
                logger.warning(
                    f"Invalid end time format provided by user: '{end_time_str}'"
                )
                continue

            if (
                end_seconds > 0 and end_seconds < start_seconds
            ):  # end_seconds=0 means full clip
                self.console.print(
                    "[red]Error: End time cannot be before start time. Please re-enter.[/red]"
                )
                logger.warning(
                    f"User provided end time ({end_seconds}) before start time ({start_seconds})."
                )
                continue

            data_packet = {
                "link": link,
                "start_time": start_seconds,
                "end_time": end_seconds,
            }
            logger.debug(f"Data packet created: {data_packet}")

            solicit_input = False

        ingestor = IngestLink(data_packet)
        ingestor.ingest_into_db()
        logger.info("Manual job setup flow finished.")

    def _parse_time_to_seconds(self, time_str):
        """
        Parses a time string (HH:MM:SS, MM:SS, or SS) into total seconds.
        Returns None if parsing fails.
        """
        if not time_str:
            return 0
        logger.debug(f"Parsing time string: '{time_str}'")

        try:
            parts = [int(p) for p in time_str.split(":")]
            seconds = 0
            if len(parts) == 3:  # HH:MM:SS
                seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
            elif len(parts) == 2:  # MM:SS
                seconds = parts[0] * 60 + parts[1]
            elif len(parts) == 1:  # SS
                seconds = parts[0]
            else:
                logger.warning(
                    f"Invalid time format: '{time_str}' has incorrect number of parts."
                )
                return None
            logger.debug(f"Parsed '{time_str}' to {seconds} seconds.")
            return seconds
        except ValueError:
            logger.error(
                f"Failed to parse time string to integer: '{time_str}'", exc_info=True
            )
            return None


class CsvJobSetup:
    """Handles the setup of jobs from a CSV file."""

    def __init__(self):
        self.console = Console()
        logger.debug("CsvJobSetup initialized.")

    def run(self):
        """The main execution method for the CSV job setup flow."""
        self.console.rule("[bold yellow]Service: CSV Job Setup[/bold yellow]")
        logger.info("Starting CSV job setup flow.")
        self.console.print("[yellow]This feature is not yet implemented.[/yellow]")
        logger.warning("CsvJobSetup.run() was called, but it is not yet implemented.")
        pass
