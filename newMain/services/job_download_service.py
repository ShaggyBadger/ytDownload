"""
This module handles services related to downloading videos. It includes functions
to manage download tasks and interact with the database to store video information.
"""

import logging
import time
import subprocess
import os
from pathlib import Path
from sqlalchemy import or_
import yt_dlp
from pydub import AudioSegment

from rich.console import Console
from rich.prompt import Prompt

from database.session_manager import get_session
from database.models import VideoInfo, JobInfo, JobStage, StageState, utcnow
from config import config

logger = logging.getLogger(__name__)


class Downloader:
    def __init__(self):
        self.console = Console()
        logger.debug("Downloader service initialized.")

    def run_all(self):
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
        except Exception as e:
            logger.critical(
                "An unexpected error occurred during run_all job processing loop.",
                exc_info=True,
            )

    def run_one(self):
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
        job_id = job_package.get("job_id")
        logger.info(f"Starting download and trim process for Job ID: {job_id}")

        try:
            with get_session() as session:
                job_stage = (
                    session.query(JobStage)
                    .filter_by(job_id=job_id, stage_name="download_video")
                    .first()
                )
                if job_stage:
                    logger.debug(
                        f"Updating Job ID {job_id}, Stage 'download_video' to RUNNING."
                    )
                    job_stage.state = StageState.running
                    job_stage.started_at = utcnow()
                    session.commit()

            # --- HOOKS for yt-dlp ---
            def progress_hook(d):
                if d.get("status") == "downloading":
                    logger.debug(
                        f"yt-dlp progress: {d['_percent_str']} of {d['_total_bytes_str']} at {d['_speed_str']}"
                    )
                if d.get("status") == "finished":
                    logger.info("yt-dlp download finished.")

            def postprocessor_hook(d):
                if d.get("status") == "started":
                    logger.info(
                        f"yt-dlp post-processing started: {d.get('postprocessor')}"
                    )
                if d.get("status") == "finished":
                    logger.info("yt-dlp post-processing finished.")

            # ------------------------

            full_audio_path = job_package.get("job_dir") / config.FULL_MP3_NAME
            trimmed_audio_path = job_package.get("job_dir") / config.MP3_SEGMENT_NAME
            logger.debug(f"Full audio path set to: {full_audio_path}")
            logger.debug(f"Trimmed audio path set to: {trimmed_audio_path}")

            ydl_opts = {
                "format": "m4a/bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
                "outtmpl": str(full_audio_path).replace(".mp3", ""),
                "keepvideo": False,
                "progress_hooks": [progress_hook],
                "postprocessor_hooks": [postprocessor_hook],
                "extractor_args": {"youtube": {"player_client": ["android"]}},
            }
            logger.debug(f"yt-dlp options: {ydl_opts}")

            with self.console.status(
                f"[bold green]Downloading {job_package.get('video_url')}...",
                spinner=config.SPINNER,
            ):
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([job_package.get("video_url")])

            with self.console.status(
                "[bold green]Trimming audio...", spinner=config.SPINNER
            ):
                logger.info(f"Loading {full_audio_path} for trimming.")
                audio = AudioSegment.from_file(full_audio_path)
                start_ms = job_package.get("audio_start_time") * 1000
                end_ms = (
                    job_package.get("audio_end_time") * 1000
                    if job_package.get("audio_end_time") > 0
                    else len(audio)
                )
                logger.info(f"Trimming audio from {start_ms}ms to {end_ms}ms.")
                trimmed_audio = audio[start_ms:end_ms]
                trimmed_audio.export(trimmed_audio_path, format="mp3")
                logger.info(
                    f"Successfully exported trimmed audio to {trimmed_audio_path}"
                )

            self._secure_delete_file(full_audio_path)

            with get_session() as session:
                logger.debug(f"Updating final stage statuses for Job ID {job_id}.")
                dl_stage = (
                    session.query(JobStage)
                    .filter_by(job_id=job_id, stage_name="download_video")
                    .first()
                )
                ea_stage = (
                    session.query(JobStage)
                    .filter_by(job_id=job_id, stage_name="extract_audio")
                    .first()
                )

                if dl_stage:
                    dl_stage.state = StageState.success
                    dl_stage.finished_at = utcnow()
                    logger.info(
                        f"Set Job ID {job_id} Stage 'download_video' to SUCCESS."
                    )

                if ea_stage:
                    ea_stage.state = StageState.success
                    ea_stage.finished_at = utcnow()
                    ea_stage.output_path = str(trimmed_audio_path)
                    logger.info(
                        f"Set Job ID {job_id} Stage 'extract_audio' to SUCCESS with output path: {trimmed_audio_path}"
                    )

                session.commit()
            self.console.print(f"Successfully processed job {job_id}.", style="green")
        except Exception:
            logger.error(
                f"A critical error occurred during the download/trim process for Job ID {job_id}.",
                exc_info=True,
            )
            with get_session() as session:
                job_stage = (
                    session.query(JobStage)
                    .filter_by(job_id=job_id, stage_name="download_video")
                    .first()
                )
                if job_stage:
                    job_stage.state = StageState.failed
                    job_stage.finished_at = utcnow()
                    job_stage.last_error = "Check logs for details."
                    session.commit()
                    logger.info(
                        f"Set Job ID {job_id} Stage 'download_video' to FAILED in database."
                    )
            self.console.print(
                f"Error processing job {job_id}. Check logs for details.", style="red"
            )

    def _secure_delete_file(self, file_path: Path):
        logger.info(f"Attempting to securely delete file: {file_path}")
        if not file_path.exists():
            logger.warning(f"File not found for secure deletion: {file_path}")
            return

        try:
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
