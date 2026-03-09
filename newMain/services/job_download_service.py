"""
This module handles services related to downloading videos. It includes functions
to manage download tasks and interact with the database to store video information.
"""

import logging
import time
import random
import subprocess
import os
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import or_
import yt_dlp
from pydub import AudioSegment

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

from database.session_manager import get_session
from database.models import VideoInfo, JobInfo, JobStage, StageState, utcnow
from config import config

logger = logging.getLogger(__name__)


class Downloader:
    """
    Service class responsible for downloading and processing audio from YouTube.

    The Downloader manages the lifecycle of a download job, including:
    - Managing database state transitions (Pending -> Running -> Success/Failed).
    - Executing yt-dlp to download high-quality audio with bot-detection bypass.
    - Handling common YouTube edge cases like recently ended live streams.
    - Providing visual timing analysis when VOD processing is incomplete.
    - Trimming audio to user-specified segments using pydub.
    - Securely cleaning up temporary files after processing.
    """

    def __init__(self):
        self.console = Console()
        logger.debug("Downloader service initialized.")

    def run_all(self):
        """Processes all pending or failed download jobs in the database."""
        logger.info("Starting run_all to process all pending/failed download jobs.")
        try:
            jobs = self._build_available_jobs()
            if not jobs:
                self.console.print("No pending jobs to download.", style="yellow")
                logger.info("No pending or failed download jobs found in run_all.")
                return

            logger.info(f"Found {len(jobs)} jobs to process.")
            for job in jobs:
                self._download_job(job)
                time.sleep(
                    random.uniform(1, 3)
                )  # Sleep to avoid overwhelming resources
        except Exception as e:
            logger.critical(
                "An unexpected error occurred during run_all job processing loop.",
                exc_info=True,
            )

    def run_one(self):
        """Allows the user to select a single eligible job for manual download."""
        logger.info(
            "Starting run_one to allow user to select a single job for download."
        )
        try:
            with get_session() as session:
                query = (
                    session.query(JobInfo)
                    .join(JobStage)
                    .filter(
                        JobStage.stage_name == "download_video",
                        or_(
                            JobStage.state == StageState.pending,
                            JobStage.state == StageState.failed,
                        ),
                    )
                )
                available_jobs = query.all()

                if not available_jobs:
                    self.console.print(
                        "No jobs available for download.", style="yellow"
                    )
                    logger.info(
                        "User initiated run_one, but no jobs were available for download."
                    )
                    return

                job_choices = {str(job.id): job for job in available_jobs}
                self.console.print("\n[bold]Select a job to download:[/bold]")
                for job_id, job in job_choices.items():
                    self.console.print(f"  [green]{job_id}[/green]: {job.video.title}")

                while True:
                    choice = Prompt.ask(
                        "Enter job ID to download (or 'q' to quit)",
                        choices=list(job_choices.keys()) + ["q"],
                    ).strip()
                    logger.debug(f"User selected option: '{choice}'")

                    if choice == "q":
                        self.console.print("Exiting job selection.", style="yellow")
                        logger.info("User chose to quit job selection.")
                        return

                    selected_job = job_choices.get(choice)
                    if selected_job:
                        job_package = self._build_job_package(selected_job)
                        self.console.print(
                            f"Selected job [green]{selected_job.id}[/green]: {selected_job.video.title}",
                            style="bold green",
                        )
                        self._download_job(job_package)
                        return
                    else:
                        self.console.print(
                            "[red]Invalid job ID. Please try again.[/red]"
                        )
                        logger.warning(f"User entered an invalid job ID: '{choice}'")
        except Exception as e:
            logger.critical(
                "A critical error occurred during the run_one job selection process.",
                exc_info=True,
            )

    def _build_job_package(self, job: JobInfo) -> dict:
        """Builds the job package dictionary for a given JobInfo object."""
        package = {
            "job_id": job.id,
            "job_dir": Path(job.job_directory),
            "audio_start_time": job.audio_start_time,
            "audio_end_time": job.audio_end_time,
            "video_title": job.video.title,
            "video_upload_date": job.video.upload_date,
            "video_description": job.video.description,
            "video_url": job.video.webpage_url,
        }
        logger.debug(f"Built job package for Job ID {job.id}")
        return package

    def _build_available_jobs(self) -> list:
        """Returns a list of dicts with job info for all pending/failed download jobs."""
        logger.debug("Building list of available jobs for download.")
        with get_session() as session:
            pending_jobs = (
                session.query(JobInfo)
                .join(JobStage)
                .filter(
                    JobStage.stage_name == "download_video",
                    or_(
                        JobStage.state == StageState.pending,
                        JobStage.state == StageState.failed,
                    ),
                )
                .all()
            )

            if not pending_jobs:
                logger.info("Query found no pending or failed jobs for download.")
                return []

            logger.info(f"Query found {len(pending_jobs)} jobs for download.")
            job_list = [self._build_job_package(job) for job in pending_jobs]
            return job_list

    def _download_job(self, job_package: dict):
        """
        Orchestrates the complete download and trim workflow for a single job.

        This method executes a sequential pipeline:
        1. Database Sync: Transitions the 'download_video' stage to 'running'.
        2. Audio Download: Uses yt-dlp with a smart fallback for new VODs.
        3. Audio Trimming: Extracts the specific time segment requested.
        4. Cleanup: Securely deletes the full-length source audio.
        5. Finalization: Updates the database with success status and file paths.

        Args:
            job_package (dict): Contains Job ID, URL, directory path, and trim times.
        """
        job_id = job_package.get("job_id")
        logger.info(f"Initiating download/trim pipeline for Job ID: {job_id}")

        try:
            # --- 1. Database State Update ---
            # Mark the stage as 'running' to provide visibility and prevent duplicates.
            with get_session() as session:
                job_stage = (
                    session.query(JobStage)
                    .filter_by(job_id=job_id, stage_name="download_video")
                    .first()
                )
                if job_stage:
                    logger.debug(f"Marking Job {job_id} Stage 'download_video' as RUNNING.")
                    job_stage.state = StageState.running
                    job_stage.started_at = utcnow()
                    session.commit()

            # --- yt-dlp Event Hooks ---
            def progress_hook(d):
                if d.get("status") == "downloading":
                    logger.debug(f"yt-dlp Progress: {d.get('_percent_str', '0%')} at {d.get('_speed_str', 'N/A')}")
                if d.get("status") == "finished":
                    logger.info("yt-dlp download byte-transfer complete.")

            def postprocessor_hook(d):
                if d.get("status") == "started":
                    logger.info(f"yt-dlp starting post-processor: {d.get('postprocessor')}")
                if d.get("status") == "finished":
                    logger.info(f"yt-dlp finished post-processor: {d.get('postprocessor')}")

            # --- 2. Path Configuration ---
            full_audio_path = job_package.get("job_dir") / config.FULL_MP3_NAME
            trimmed_audio_path = job_package.get("job_dir") / config.MP3_SEGMENT_NAME
            logger.debug(f"Targeting paths: Full={full_audio_path}, Segment={trimmed_audio_path}")

            # --- 3. yt-dlp Configuration ---
            # Audio-only extraction with browser cookie and remote JS support.
            ydl_opts = {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
                "outtmpl": {"default": str(full_audio_path.with_suffix(".%(ext)s"))},
                "keepvideo": False,
                "progress_hooks": [progress_hook],
                "postprocessor_hooks": [postprocessor_hook],
                "cookiesfrombrowser": ("firefox",),
                "extractor_args": {
                    "youtube": {"player_client": ["web", "android", "web_safari"]}
                },
                "remote_components": ["ejs:github"], # Use remote JS solver for reliability
            }

            def perform_download(options):
                """Helper to execute the actual download within a Rich status spinner."""
                with self.console.status(
                    f"[bold green]Downloading {job_package.get('video_url')}...",
                    spinner=config.SPINNER,
                ):
                    with yt_dlp.YoutubeDL(options) as ydl:
                        ydl.download([job_package.get("video_url")])

            # --- 4. Execution with Failure Interception ---
            try:
                logger.debug(f"Attempting initial download for Job {job_id}")
                perform_download(ydl_opts)
            except yt_dlp.utils.DownloadError as e:
                # If formats are missing, it's likely a recently ended live stream.
                error_msg = str(e)
                if "No video formats found" in error_msg or "This live event has ended" in error_msg:
                    logger.warning(f"Download failed for Job {job_id} (Dead Zone detected). Error: {error_msg}")
                    
                    # Show user exactly why it might be failing based on time since release.
                    self._display_timing_report(job_package.get("video_url"))
                    
                    self.console.print("\n") # Visual spacing
                    if Confirm.ask(
                        f"[yellow]Download failed for Job {job_id}: Video not ready yet.[/yellow]\n"
                        f"[bold cyan]Retry with 'ignore_no_formats_error' enabled?[/bold cyan]"
                    ):
                        logger.info(f"User requested retry with bypass flag for Job {job_id}.")
                        ydl_opts["ignore_no_formats_error"] = True
                        perform_download(ydl_opts)
                    else:
                        logger.info(f"User declined retry for Job {job_id}. Aborting.")
                        raise
                else:
                    # Rethrow other download errors (e.g., 403 Forbidden, Private Video)
                    raise

            # --- 5. Audio Trimming ---
            with self.console.status("[bold green]Trimming audio segment...", spinner=config.SPINNER):
                logger.info(f"Loading {full_audio_path} for segment extraction.")
                audio = AudioSegment.from_file(full_audio_path)
                
                start_ms = job_package.get("audio_start_time") * 1000
                end_ms = (
                    job_package.get("audio_end_time") * 1000
                    if job_package.get("audio_end_time") > 0
                    else len(audio)
                )
                
                logger.info(f"Extracting segment: {start_ms}ms to {end_ms}ms.")
                trimmed_audio = audio[start_ms:end_ms]
                trimmed_audio.export(trimmed_audio_path, format="mp3")
                logger.info(f"Trimmed audio exported to: {trimmed_audio_path}")

            # --- 6. Secure Cleanup ---
            self._secure_delete_file(full_audio_path)

            # --- 7. Finalize Database State ---
            with get_session() as session:
                logger.debug(f"Updating completion statuses for Job ID {job_id}.")
                dl_stage = session.query(JobStage).filter_by(job_id=job_id, stage_name="download_video").first()
                ea_stage = session.query(JobStage).filter_by(job_id=job_id, stage_name="extract_audio").first()

                if dl_stage:
                    dl_stage.state = StageState.success
                    dl_stage.finished_at = utcnow()
                    logger.info(f"Job {job_id} 'download_video' finalizing: SUCCESS")

                if ea_stage:
                    ea_stage.state = StageState.success
                    ea_stage.finished_at = utcnow()
                    ea_stage.output_path = str(trimmed_audio_path)
                    logger.info(f"Job {job_id} 'extract_audio' finalizing: SUCCESS")

                session.commit()
            
            self.console.print(f"Successfully processed Job {job_id}.", style="green")

        except Exception as e:
            logger.error(f"Critical error in Job {job_id} pipeline: {e}", exc_info=True)
            self._handle_job_failure(job_id, str(e))

    def _handle_job_failure(self, job_id: int, error_msg: str):
        """Helper to mark a job stage as failed in the database."""
        with get_session() as session:
            job_stage = session.query(JobStage).filter_by(job_id=job_id, stage_name="download_video").first()
            if job_stage:
                job_stage.state = StageState.failed
                job_stage.finished_at = utcnow()
                job_stage.last_error = error_msg
                session.commit()
                logger.info(f"Job {job_id} 'download_video' stage marked as FAILED in database.")
        self.console.print(f"Error processing job {job_id}. See logs for details.", style="red")

    def _display_timing_report(self, url: str):
        """
        Analyzes video release timing and displays a detailed report.

        This performs an on-the-fly metadata fetch to determine if a download failure
        is likely due to pending VOD processing on YouTube's backend.
        """
        logger.info(f"Running VOD readiness analysis for URL: {url}")
        
        ydl_opts = {
            "cookiesfrombrowser": ("firefox",),
            "remote_components": ["ejs:github"],
            "extractor_args": {"youtube": {"player_client": ["web", "android", "web_safari"]}},
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "ignore_no_formats_error": True, # Required to get metadata during dead zone
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Use release_timestamp (live end) or timestamp (regular video start)
                ts = info.get("release_timestamp") or info.get("timestamp")
                
                if ts:
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    now = datetime.now(timezone.utc)
                    diff = now - dt
                    
                    total_minutes = int(diff.total_seconds() / 60)
                    hours = total_minutes // 60
                    minutes = total_minutes % 60
                    
                    # Build and display the report panel
                    report = (
                        f"[bold white]Video Title:[/bold white] {info.get('title')}\n"
                        f"[bold white]Live Status:[/bold white] {info.get('live_status', 'N/A')}\n"
                        f"[bold white]Event Ended:[/bold white] {dt.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                        f"[bold white]Current Time:[/bold white] {now.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                        f"[bold white]Time Elapsed:[/bold white] [bold yellow]{hours}h {minutes}m[/bold yellow]\n\n"
                    )
                    
                    if total_minutes < 60:
                        report += (
                            "[bold red]CRITICAL: This stream ended very recently.[/bold red]\n"
                            "YouTube usually requires [bold yellow]30-60 minutes[/bold yellow] to generate the\n"
                            "high-quality VOD audio files after a stream ends."
                        )
                    else:
                        report += (
                            "[bold green]ANALYSIS: Sufficient time has likely passed for VOD processing.[/bold green]\n"
                            "If failure persists, check for regional blocks or availability issues."
                        )

                    self.console.print("\n")
                    self.console.print(Panel(
                        report, 
                        title="[bold cyan]VOD Readiness Analysis[/bold cyan]", 
                        border_style="cyan",
                        expand=False
                    ))
                else:
                    logger.warning(f"No valid timestamp found in metadata for {url}.")
                    self.console.print("[yellow]Could not determine exact release time for this video.[/yellow]")
        except Exception as e:
            logger.error(f"Failed to generate timing report: {e}", exc_info=True)

    def _secure_delete_file(self, file_path: Path):
        """Attempts to securely delete a file using 'shred', falling back to os.remove."""
        logger.info(f"Attempting to securely delete file: {file_path}")
        if not file_path.exists():
            logger.warning(f"File not found for secure deletion: {file_path}")
            return

        try:
            # Use GNU shred to overwrite and delete the file.
            cmd = ["shred", "-uz", str(file_path)]
            logger.debug(f"Running secure delete command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Securely deleted: {file_path}")
            if result.stdout:
                logger.debug(f"Shred stdout: {result.stdout.strip()}")
            if result.stderr:
                logger.warning(f"Shred stderr: {result.stderr.strip()}")
        except FileNotFoundError:
            logger.warning("shred command not found. Falling back to os.remove().")
            try:
                os.remove(file_path)
                logger.info(f"Insecurely deleted (os.remove): {file_path}")
            except OSError:
                logger.error(
                    f"Error during fallback deletion of {file_path} with os.remove().",
                    exc_info=True,
                )
        except subprocess.CalledProcessError as e:
            logger.error(f"Shred command failed for {file_path}.", exc_info=True)
            if e.stdout:
                logger.error(f"Shred stdout: {e.stdout.strip()}")
            if e.stderr:
                logger.error(f"Shred stderr: {e.stderr.strip()}")
        except Exception:
            logger.critical(
                f"An unexpected critical error occurred during deletion of {file_path}.",
                exc_info=True,
            )
