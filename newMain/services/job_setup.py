"""
This module provides core services for setting up and ingesting new video processing jobs
into the application's database. It handles both manual entry of video links and
batch processing from a CSV file.

Key functionalities include:
- Extracting YouTube video IDs and fetching metadata using yt-dlp.
- Storing video and job-specific information in the SQLite database via SQLAlchemy.
- Orchestrating the creation of initial processing stages for each job.
- For CSV-based ingestion, it includes logic to:
    - Skip already processed rows (marked with 'x' in a 'Done' column).
    - Detect existing videos in the database based on URL and prompt the user for
      confirmation before creating a new job for the same video.
    - Persist changes (marking rows as 'Done') back to the CSV file.

The module aims for robust error handling and comprehensive logging to aid in
debugging and operational monitoring.
"""

import logging
import re
from datetime import datetime, timedelta
import yt_dlp
import csv
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from database.session_manager import get_session
from database.models import VideoInfo, JobInfo, JobStage, StageState, STAGE_ORDER
from config.config import build_job_directory_path

# Initialize logger for this module
logger = logging.getLogger(__name__)


class IngestLink:
    """
    Handles the ingestion of a single video link into the database.
    This includes extracting YouTube ID, fetching metadata, and creating
    VideoInfo, JobInfo, and initial JobStage entries.
    """

    def __init__(self, data_packet: dict):
        """
        Initializes the IngestLink with video link and trim times.

        Args:
            data_packet (dict): A dictionary containing 'link', 'start_time' (seconds),
                                'end_time' (seconds) for the video.
        """
        self.link = data_packet.get("link")
        self.start_seconds = data_packet.get(
            "start_time"
        )  # Audio start time in seconds
        self.end_seconds = data_packet.get("end_time")  # Audio end time in seconds
        self.console = Console()  # Rich console for user output
        logger.debug(
            f"IngestLink initialized for link: '{self.link}', start: {self.start_seconds}s, end: {self.end_seconds}s"
        )

    def _extract_yt_id(self, url: str) -> str | None:
        """
        Extracts the YouTube video ID from a given URL.
        Supports standard, shortened (youtu.be), and embed URLs.

        Args:
            url (str): The YouTube video URL.

        Returns:
            str | None: The extracted YouTube video ID, or None if not found.
        """
        if not url:
            logger.warning(
                "Attempted to extract YouTube ID from a null or empty URL. Returning None."
            )
            return None
        logger.debug(f"Attempting to extract YouTube ID from URL: '{url}'")

        # Regex to match various YouTube URL formats
        youtube_regex = (
            r"(?:https?://)?(?:www\.)?"
            r"(?:youtube\.com/(?:watch\?v=|embed/|v/)|youtu\.be/)"
            r"([a-zA-Z0-9_-]{11})"  # Captures the 11-character video ID
        )
        match = re.search(youtube_regex, url)
        if match:
            yt_id = match.group(1)
            logger.debug(
                f"Successfully extracted YouTube ID: '{yt_id}' from URL: '{url}'"
            )
            return yt_id

        logger.warning(
            f"Could not extract a valid YouTube ID from URL: '{url}'. Returning None."
        )
        return None

    def _get_video_metadata(self, url: str) -> dict:
        """
        Fetches video metadata using yt-dlp without downloading the video.
        Configured to use browser cookies and remote components for robustness.

        Args:
            url (str): The YouTube video URL to fetch metadata for.

        Returns:
            dict: A dictionary containing relevant video metadata, or an empty dict on failure.
        """
        logger.info(f"Fetching metadata with yt-dlp for URL: '{url}'")
        # yt-dlp options to fetch info only, use browser cookies, and enable remote JS solver
        ydl_opts = {
            "cookiesfrombrowser": ("firefox",),
            "remote_components": ["ejs:github"],
            "extractor_args": {
                "youtube": {"player_client": ["web", "android", "web_safari"]}
            },
            "skip_download": True,
            "extract_flat": False,
            "quiet": True,
            "no_warnings": True,
        }

        logger.debug(f"yt-dlp options for metadata extraction: {ydl_opts}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Remove timestamp from URL to ensure consistent metadata fetching
                cleaned_url = url.split("&t=")[0]
                logger.debug(f"Cleaned URL for yt-dlp: '{cleaned_url}'")
                info_dict = ydl.extract_info(cleaned_url, download=False)
                logger.debug(
                    f"Raw info_dict received from yt-dlp for '{cleaned_url}': {info_dict}"
                )

                # Extract specific fields from the info_dict
                video_details = {
                    "yt_id": info_dict.get("id"),
                    "title": info_dict.get("title"),
                    "uploader": info_dict.get("uploader"),
                    "channel_id": info_dict.get("channel_id"),
                    "channel_url": info_dict.get("channel_url"),
                    "upload_date": info_dict.get("upload_date"),  # Format YYYYMMDD
                    "duration": info_dict.get("duration"),  # In seconds
                    "webpage_url": info_dict.get("webpage_url"),
                    "description": info_dict.get("description"),
                    "thumbnail": info_dict.get("thumbnail"),
                    "was_live": info_dict.get("was_live"),
                    "live_status": info_dict.get("live_status"),
                }
                logger.debug(
                    f"Successfully fetched and parsed metadata for yt_id: '{video_details.get('yt_id')}': {video_details}"
                )
                return video_details
        except yt_dlp.utils.DownloadError as e:
            logger.error(
                f"yt-dlp failed to fetch metadata for URL: '{url}'. Error: {e}",
                exc_info=True,
            )
            return {}
        except Exception as e:
            logger.critical(
                f"An unexpected error occurred during yt-dlp metadata extraction for '{url}'. Error: {e}",
                exc_info=True,
            )
            return {}

    def ingest_into_db(self) -> int | None:
        """
        Ingests the video link information and job details into the database.
        This involves creating or retrieving VideoInfo, then creating JobInfo and
        associated JobStage entries.

        Returns:
            int | None: The ID of the newly created JobInfo object on success, None on failure.
        """
        logger.info(f"Starting database ingestion process for link: '{self.link}'")
        yt_id = self._extract_yt_id(self.link)
        if not yt_id:
            logger.error(
                f"Could not ingest link because YouTube ID extraction failed for: '{self.link}'. Aborting ingestion."
            )
            return None

        job_id = None
        try:
            with get_session() as session:
                # 1. Find or create VideoInfo entry
                logger.debug(
                    f"Attempting to find existing VideoInfo with yt_id: '{yt_id}'"
                )
                video_info = session.query(VideoInfo).filter_by(yt_id=yt_id).first()

                if not video_info:
                    logger.info(
                        f"No existing VideoInfo found for yt_id: '{yt_id}'. Proceeding to fetch new metadata."
                    )
                    metadata = self._get_video_metadata(self.link)

                    if not metadata:
                        logger.error(
                            f"Failed to fetch metadata for '{self.link}'. Cannot create VideoInfo. Aborting ingestion."
                        )
                        return None

                    # Ensure yt_id from metadata matches the extracted one to prevent inconsistencies
                    if metadata.get("yt_id") != yt_id:
                        logger.error(
                            f"Metadata yt_id '{metadata.get('yt_id')}' does not match extracted yt_id '{yt_id}' for link '{self.link}'. Aborting."
                        )
                        return None

                    video_info = VideoInfo(**metadata)
                    session.add(video_info)
                    session.flush()  # Assigns an ID to video_info before commit
                    logger.info(
                        f"New VideoInfo created with ID: {video_info.id} for yt_id: '{yt_id}' and title: '{video_info.title}'"
                    )
                else:
                    logger.info(
                        f"Found existing VideoInfo with ID: {video_info.id} for yt_id: '{yt_id}' and title: '{video_info.title}'"
                    )

                # 2. Create JobInfo entry for the new job
                new_job = JobInfo(
                    video_id=video_info.id,
                    audio_start_time=self.start_seconds,
                    audio_end_time=self.end_seconds,
                )
                session.add(new_job)
                session.flush()  # Assigns an ID to new_job before commit
                logger.debug(
                    f"New JobInfo object created with temporary ID: {new_job.id} and generated ULID: '{new_job.job_ulid}'"
                )

                # Determine and set the job's dedicated directory path
                new_job.job_directory = build_job_directory_path(
                    new_job.job_ulid, new_job.id
                )
                logger.info(
                    f"Set job directory for Job ID {new_job.id} (ULID: '{new_job.job_ulid}') to: '{new_job.job_directory}'"
                )

                # 3. Create JobStage entries for all defined pipeline stages
                logger.debug(
                    f"Creating {len(STAGE_ORDER)} JobStage entries for new Job ID {new_job.id}."
                )
                for stage_name in STAGE_ORDER:
                    job_stage = JobStage(
                        job_id=new_job.id,
                        stage_name=stage_name,
                        state=StageState.pending,  # All new stages start as pending
                    )
                    session.add(job_stage)
                    logger.debug(
                        f"Added JobStage: '{stage_name}' for Job ID {new_job.id}, initial state: {StageState.pending.value}"
                    )

                session.commit()  # Persist all changes to the database
                job_id = new_job.id
                logger.info(
                    f"Successfully committed Job ID {job_id} and its {len(STAGE_ORDER)} associated stages to the database."
                )
                self.console.print(
                    f"[bold green]Successfully ingested job for '{self.link}' (Job ID: {job_id})[/bold green]"
                )
                return job_id
        except Exception as e:
            session.rollback()  # Rollback transaction on error to prevent partial writes
            logger.critical(
                f"A critical error occurred during the database transaction for link '{self.link}'. Rolling back. Error: {e}",
                exc_info=True,
            )
            self.console.print(
                "[bold red]A critical error occurred during ingestion. Check the logs for details.[/bold red]"
            )
            return None


class ManualJobSetup:
    """
    Manages the interactive setup process for a single job through manual user input.
    Prompts for URL, start/end times, and then delegates to IngestLink.
    """

    def __init__(self):
        """
        Initializes ManualJobSetup, including a Rich console for output.
        """
        self.console = Console()
        logger.debug("ManualJobSetup service initialized.")

    def run(self):
        """
        The main execution method for the manual job setup flow.
        Guides the user through entering video details and ingests them.
        """
        self.console.clear()  # Clear console for cleaner user experience
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

            # Input validation for start time
            if start_seconds is None:
                self.console.print(
                    f"[red]Error: Invalid start time format: '{start_time_str}'. Please use HH:MM:SS, MM:SS, or SS.[/red]"
                )
                logger.warning(
                    f"Invalid start time format provided by user: '{start_time_str}'. Reprompting."
                )
                continue

            # Input validation for end time
            if end_seconds is None:
                self.console.print(
                    f"[red]Error: Invalid end time format: '{end_time_str}'. Please use HH:MM:SS, MM:SS, or SS.[/red]"
                )
                logger.warning(
                    f"Invalid end time format provided by user: '{end_time_str}'. Reprompting."
                )
                continue

            # Logic check: end time must not be before start time (unless end_seconds is 0, meaning full clip)
            if (end_seconds > 0) and (end_seconds < start_seconds):
                self.console.print(
                    "[red]Error: End time cannot be before start time. Please re-enter.[/red]"
                )
                logger.warning(
                    f"User provided end time ({end_seconds}) before start time ({start_seconds}). Reprompting."
                )
                continue

            # If all validations pass, prepare data packet for ingestion
            data_packet = {
                "link": link,
                "start_time": start_seconds,
                "end_time": end_seconds,
            }
            logger.debug(f"Data packet created for manual ingestion: {data_packet}")

            solicit_input = False  # Exit loop if input is valid

        ingestor = IngestLink(data_packet)
        ingestor.ingest_into_db()  # Delegate to IngestLink for database operations
        logger.info("Manual job setup flow finished.")

    def _parse_time_to_seconds(self, time_str: str) -> int | None:
        """
        Parses a time string (HH:MM:SS, MM:SS, or SS) into total seconds.

        Args:
            time_str (str): The time string to parse.

        Returns:
            int | None: Total seconds, or None if parsing fails.
        """
        if not time_str:
            logger.debug("Empty time string provided, defaulting to 0 seconds.")
            return 0
        logger.debug(f"Parsing time string: '{time_str}' into seconds.")

        try:
            parts = [int(p) for p in time_str.split(":")]
            seconds = 0
            if len(parts) == 3:  # HH:MM:SS format
                seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
                logger.debug(f"Parsed '{time_str}' as HH:MM:SS to {seconds} seconds.")
            elif len(parts) == 2:  # MM:SS format
                seconds = parts[0] * 60 + parts[1]
                logger.debug(f"Parsed '{time_str}' as MM:SS to {seconds} seconds.")
            elif len(parts) == 1:  # SS format
                seconds = parts[0]
                logger.debug(f"Parsed '{time_str}' as SS to {seconds} seconds.")
            else:
                logger.warning(
                    f"Invalid time format: '{time_str}' has an incorrect number of parts. Expected HH:MM:SS, MM:SS, or SS."
                )
                return None
            logger.debug(f"Successfully parsed '{time_str}' to {seconds} seconds.")
            return seconds
        except ValueError as e:
            logger.error(
                f"Failed to parse time string '{time_str}' to integer (ValueError: {e}). Returning None.",
                exc_info=True,
            )
            return None


class CsvJobSetup:
    """
    Handles the setup of multiple jobs from a CSV file.
    It reads the CSV, processes each row, checks for duplicates,
    prompts the user if needed, ingests data, and updates the CSV.
    """

    def __init__(self):
        """
        Initializes CsvJobSetup, setting up the console and defining the CSV file path.
        """
        self.console = Console()
        # The CSV file is expected to be in the parent directory of this module
        self.csv = Path(__file__).parent.parent / "video_urls.csv"
        logger.debug(f"CsvJobSetup initialized. CSV file path set to: '{self.csv}'")

    def run(self):
        """
        The main execution method for the CSV job setup flow.
        Orchestrates the reading, processing, and writing back of the CSV file.
        """
        self.console.rule("[bold yellow]Service: CSV Job Setup[/bold yellow]")
        logger.info(f"Starting CSV job setup flow. Processing CSV file: '{self.csv}'")
        self._process_csv()
        logger.info("CSV job setup flow finished.")

    def _process_csv(self):
        """
        Reads the CSV file, processes each row for video ingestion,
        handles duplicates, and updates the 'Done' column.
        Finally, it writes all changes back to the CSV.
        """
        logger.info(f"Beginning to process CSV file at: '{self.csv}'")
        updated_rows = (
            []
        )  # List to hold all rows (original and modified) for writing back
        rows_to_process = []  # List to temporarily hold rows read from CSV

        try:
            # Read all rows from the CSV into memory
            with open(self.csv, mode="r", newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                rows_to_process = list(reader)
            logger.debug(f"Read {len(rows_to_process)} rows from CSV.")

            if not rows_to_process:
                self.console.print("No rows found in CSV to process.", style="yellow")
                logger.info(
                    "CSV file is empty or contains no parsable rows. Exiting CSV processing."
                )
                return

            # Iterate through each row for processing
            for i, row in enumerate(rows_to_process):
                current_row = (
                    row.copy()
                )  # Work on a copy to avoid modifying list during iteration
                row_identifier = f"Row {i+1} (URL: '{current_row.get('url', 'N/A')}')"
                logger.debug(f"Processing {row_identifier}: {current_row}")

                # 1. Check if row is already marked as 'Done'
                complete_status = current_row.get("Done", "").lower()
                if complete_status == "x":
                    logger.info(
                        f"{row_identifier} is already marked 'Done'. Skipping ingestion."
                    )
                    updated_rows.append(current_row)  # Add to list for writing back
                    continue  # Move to next row

                # 2. Extract URL and validate its presence
                url = current_row.get("url")
                if not url:
                    logger.warning(
                        f"{row_identifier} has no URL. Skipping ingestion for this row."
                    )
                    updated_rows.append(current_row)  # Add original row to list
                    continue  # Move to next row

                # Extract time strings from the current CSV row
                start_time_str = f"{current_row.get('start_hour', '0')}:{current_row.get('start_min', '0')}:{current_row.get('start_sec', '0')}"
                end_time_str = f"{current_row.get('end_hour', '0')}:{current_row.get('end_min', '0')}:{current_row.get('end_sec', '0')}"
                logger.debug(
                    f"{row_identifier} - Extracted start_time_str: '{start_time_str}', end_time_str: '{end_time_str}'"
                )

                # 3. Check for existing video in DB and confirm ingestion with user
                # This call handles user interaction if a duplicate URL is found
                should_proceed = self._confirm_ingestion_if_video_exists(
                    url, start_time_str, end_time_str
                )
                if not should_proceed:
                    logger.info(
                        f"User chose to skip ingestion for {row_identifier} due to existing video."
                    )
                    updated_rows.append(current_row)  # Add original row to list
                    continue  # Move to next row

                # 4. Ingest the job into the database
                logger.info(f"Proceeding to ingest job for {row_identifier}.")
                ingestor = IngestLink(
                    {
                        "link": url,
                        "start_time": self._parse_time_to_seconds(start_time_str),
                        "end_time": self._parse_time_to_seconds(end_time_str),
                    }
                )
                job_id = (
                    ingestor.ingest_into_db()
                )  # Returns Job ID on success, None on failure

                # 5. Update 'Done' status based on ingestion result
                if job_id:
                    current_row["Done"] = (
                        "x"  # Mark as done if ingestion was successful
                    )
                    logger.info(
                        f"{row_identifier} successfully ingested (Job ID: {job_id}). Marked as 'Done'."
                    )
                else:
                    logger.warning(
                        f"Ingestion failed for {row_identifier}. Row not marked as 'Done'."
                    )

                updated_rows.append(
                    current_row
                )  # Add the (potentially modified) row to the list

            # 6. Write all accumulated rows back to the CSV file
            self._write_csv(updated_rows)
            logger.info(
                "Finished processing all CSV rows. CSV file has been updated with 'Done' statuses."
            )
        except FileNotFoundError:
            logger.error(
                f"CSV file not found at path: '{self.csv}'. Please ensure the file exists.",
                exc_info=True,
            )
            self.console.print(f"[red]Error: CSV file not found at '{self.csv}'[/red]")
        except Exception as e:
            logger.critical(
                f"A critical error occurred while processing the CSV file '{self.csv}'. Error: {e}",
                exc_info=True,
            )
            self.console.print(
                "[red]A critical error occurred during CSV processing. Check logs for more details.[/red]"
            )

    def _confirm_ingestion_if_video_exists(
        self, url: str, start_time: str, end_time: str
    ) -> bool:
        """
        Checks if a video with the given URL already exists in the database.
        If found, it displays existing database information and the current CSV row's
        data to the user, then prompts for confirmation to create a new job for it.

        Args:
            url (str): The video URL from the CSV row.
            start_time (str): The start time string from the CSV row.
            end_time (str): The end time string from the CSV row.

        Returns:
            bool: True if ingestion should proceed (either no existing video or user confirmed),
                  False if ingestion should be skipped.
        """
        logger.debug(f"Checking for existing video in DB for URL: '{url}'")
        try:
            with get_session() as session:
                # Query the VideoInfo table for a matching webpage_url
                video = session.query(VideoInfo).filter_by(webpage_url=url).first()
                if not video:
                    logger.debug(
                        f"No existing video found in DB for URL: '{url}'. Proceeding with ingestion."
                    )
                    return True  # No existing video, so proceed

            # If video exists, construct and display a rich table for comparison
            logger.info(
                f"Existing video found in DB for URL: '{url}'. Prompting user for action."
            )
            table = Table(
                title="[bold yellow]Existing Video Found in Database[/bold yellow]",
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Source", style="dim", width=12)
            table.add_column("Attribute", style="bold")
            table.add_column("Value")

            # Display information from the database
            table.add_row("Database", "Title", video.title)
            table.add_row("Database", "Uploader", video.uploader)
            table.add_row("Database", "Upload Date", video.upload_date)
            table.add_row("Database", "Duration (s)", str(video.duration))
            table.add_section()
            # Display information from the current CSV row
            table.add_row("CSV", "URL", url)
            table.add_row("CSV", "Start Time", start_time)
            table.add_row("CSV", "End Time", end_time)

            self.console.print(table)

            # Prompt user for decision
            user_choice = Prompt.ask(
                "A video with this URL already exists. Do you want to create a new job for it?",
                choices=["y", "n"],
                default="n",  # Default to 'n' to prevent accidental re-ingestion
            ).lower()

            if user_choice == "y":
                logger.info(
                    f"User chose to create a new job for existing video URL: '{url}'."
                )
                return True
            else:
                logger.info(
                    f"User chose NOT to create a new job for existing video URL: '{url}'. Skipping."
                )
                return False

        except Exception as e:
            logger.critical(
                f"An error occurred during video existence check for URL: '{url}'. Error: {e}",
                exc_info=True,
            )
            self.console.print(
                "[red]Could not verify if video exists in DB due to an error. Skipping to be safe.[/red]"
            )
            return False

    def _write_csv(self, rows: list[dict]):
        """
        Writes a list of dictionaries (representing CSV rows) back to the CSV file.
        This overwrites the existing file with the updated content.

        Args:
            rows (list[dict]): A list of dictionaries, where each dictionary represents a row.
                               Keys are column headers.
        """
        if not rows:
            logger.warning(
                "No rows provided to write to CSV. Skipping write operation."
            )
            return

        logger.info(
            f"Attempting to write {len(rows)} rows back to CSV file: '{self.csv}'"
        )
        try:
            # Ensure all rows have the same keys for consistent CSV structure
            # Get fieldnames from the first row, assuming it's representative
            fieldnames = list(rows[0].keys())
            logger.debug(f"CSV fieldnames determined: {fieldnames}")

            with open(self.csv, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()  # Write the header row
                writer.writerows(rows)  # Write all data rows
            logger.info(f"Successfully wrote updated CSV content to '{self.csv}'")
        except IOError as e:
            logger.error(
                f"Failed to write to CSV file: '{self.csv}' (IOError: {e}).",
                exc_info=True,
            )
            self.console.print(
                f"[red]Error: Failed to write to CSV file '{self.csv}'[/red]"
            )
        except Exception as e:
            logger.critical(
                f"An unexpected error occurred while writing to the CSV file '{self.csv}'. Error: {e}",
                exc_info=True,
            )
            self.console.print(
                "[red]A critical error occurred during CSV write. Check logs for more details.[/red]"
            )

    def _parse_time_to_seconds(self, time_str: str) -> int | None:
        """
        Parses a time string (HH:MM:SS, MM:SS, or SS) into total seconds.

        Args:
            time_str (str): The time string to parse.

        Returns:
            int | None: Total seconds, or None if parsing fails.
        """
        if not time_str:
            logger.debug("Empty time string provided, defaulting to 0 seconds.")
            return 0
        logger.debug(f"Parsing time string: '{time_str}' into seconds.")

        try:
            parts = [int(p) for p in time_str.split(":")]
            seconds = 0
            if len(parts) == 3:  # HH:MM:SS format
                seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
                logger.debug(f"Parsed '{time_str}' as HH:MM:SS to {seconds} seconds.")
            elif len(parts) == 2:  # MM:SS format
                seconds = parts[0] * 60 + parts[1]
                logger.debug(f"Parsed '{time_str}' as MM:SS to {seconds} seconds.")
            elif len(parts) == 1:  # SS format
                seconds = parts[0]
                logger.debug(f"Parsed '{time_str}' as SS to {seconds} seconds.")
            else:
                logger.warning(
                    f"Invalid time format: '{time_str}' has an incorrect number of parts. Expected HH:MM:SS, MM:SS, or SS."
                )
                return None
            logger.debug(f"Successfully parsed '{time_str}' to {seconds} seconds.")
            return seconds
        except ValueError as e:
            logger.error(
                f"Failed to parse time string '{time_str}' to integer (ValueError: {e}). Returning None.",
                exc_info=True,
            )
            return None
