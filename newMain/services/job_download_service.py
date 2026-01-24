"""
This module handles services related to downloading videos. It includes functions
to manage download tasks and interact with the database to store video information.
"""

from rich.console import Console
from rich.prompt import Prompt
import yt_dlp
from pydub import AudioSegment
from pathlib import Path
import time
import subprocess
import os
from sqlalchemy import or_

from database.session_manager import get_session
from database.models import VideoInfo, JobInfo, JobStage, StageState, STAGE_ORDER
from database.db_config import utcnow
from config import config

class Downloader:
    def __init__(self):
        self.console = Console()

    def run_all(self):
        # get list of all videos to download
        jobs = self._build_available_jobs() # gets a list of dicts
        for job in jobs:
            self._download_job(job)

    def run_one(self):
        with get_session() as session:
            # Query all jobs where the 'download_video' stage is in 'pending' or 'failed' state
            query = session.query(JobInfo).join(JobStage).filter(
                JobStage.stage_name == 'download_video',
                or_(
                    JobStage.state == StageState.pending,
                    JobStage.state == StageState.failed
                )
            )
            available_jobs = query.all()

            if not available_jobs:
                self.console.print("No jobs available for download.", style="yellow")
                return

            job_choices = {}
            self.console.print("\n[bold]Select a job to download:[/bold]")
            for job in available_jobs:
                video = session.query(VideoInfo).filter(VideoInfo.id == job.video_id).first()
                if video:
                    self.console.print(f"  [green]{job.id}[/green]: {video.title}")
                    job_choices[str(job.id)] = job
                else:
                    self.console.print(f"  [red]Skipping job {job.id} - VideoInfo not found.[/red]")

            while True:
                choice = Prompt.ask("Enter job ID to download (or 'q' to quit)", choices=list(job_choices.keys()) + ['q']).strip()
                if choice == 'q':
                    self.console.print("Exiting job selection.", style="yellow")
                    return

                selected_job = job_choices.get(choice)
                if selected_job:
                    # Build job_package for the selected job
                    video = session.query(VideoInfo).filter(VideoInfo.id == selected_job.video_id).first()
                    job_package = {
                        'job_id': selected_job.id,
                        'job_dir': Path(selected_job.job_directory),
                        'audio_start_time': selected_job.audio_start_time,
                        'audio_end_time': selected_job.audio_end_time,
                        'video_title': video.title,
                        'video_upload_date': video.upload_date,
                        'video_description': video.description,
                        'video_url': video.webpage_url
                    }
                    self.console.print(f"Selected job [green]{selected_job.id}[/green]: {video.title}", style="bold green")
                    self._download_job(job_package)
                    return
                else:
                    self.console.print("[red]Invalid job ID. Please try again.[/red]")

    
    def _build_available_jobs(self):
        """returns a list of dicts with job info"""
        with get_session() as session:
            # Query all jobs where the 'download_video' stage is in 'pending' state
            query = session.query(JobInfo)
            query = query.join(JobStage)
            query = query.filter(
                JobStage.stage_name == 'download_video',
                or_(
                    JobStage.state == StageState.pending,
                    JobStage.state == StageState.failed
                )
            )

            # Get all matching jobs in a list
            pending_jobs = query.all()

            # build dict with info needed to download and trim
            job_list = []
            for job in pending_jobs:
                # TODO: upgrade the model to have video reference in JobInfo
                # get video information
                query = session.query(VideoInfo).filter(VideoInfo.id == job.video_id)
                video = query.first()

                # build job_package
                job_package = {
                    'job_id': job.id,
                    'job_dir': Path(job.job_directory), # convert str to Path
                    'audio_start_time': job.audio_start_time,
                    'audio_end_time': job.audio_end_time,
                    'video_title': video.title,
                    'video_upload_date': video.upload_date,
                    'video_description': video.description,
                    'video_url': video.webpage_url
                }
                job_list.append(job_package)

        return job_list

    def _download_job(self, job_package):
        job_id = job_package.get('job_id')

        with get_session() as session:
            job_stage = session.query(JobStage).filter_by(
                job_id=job_id, stage_name='download_video'
            ).first()
            if job_stage:
                job_stage.state = StageState.running
                job_stage.started_at = utcnow()
                session.commit()

        try:
            # --- HOOKS for yt-dlp ---
            def progress_hook(d):
                if d.get('status') == 'downloading':
                    # Optional: Add rich console update here for live progress
                    pass
                if d.get('status') == 'finished':
                    self.console.print("Download complete.", style="green")

            def postprocessor_hook(d):
                if d.get('status') == 'started':
                    self.console.print(f"Post-processing: {d['postprocessor']}...", style="blue")
                if d.get('status') == 'finished':
                    self.console.print("Post-processing complete. Pausing for 2 seconds...", style="blue")
                    time.sleep(2)
            # ------------------------

            # Define full path for the downloaded audio
            full_audio_path = job_package.get('job_dir') / config.FULL_MP3_NAME
            trimmed_audio_path = job_package.get('job_dir') / config.MP3_SEGMENT_NAME

            # Download
            with self.console.status(f"[bold green]Downloading {job_package.get('video_url')}...", spinner="dots") as status:
                ydl_opts = {
                    'format': 'm4a/bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': str(full_audio_path).replace('.mp3', ''), # yt-dlp adds the extension
                    'keepvideo': False,
                    'progress_hooks': [progress_hook],
                    'postprocessor_hooks': [postprocessor_hook],
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['android']
                        }
                    }
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([job_package.get('video_url')])

            # Trim
            with self.console.status("[bold green]Trimming audio...", spinner="dots") as status:
                audio = AudioSegment.from_file(full_audio_path)
                start_ms = job_package.get('audio_start_time') * 1000
                end_ms = job_package.get('audio_end_time') * 1000
                trimmed_audio = audio[start_ms:end_ms]
                trimmed_audio.export(trimmed_audio_path, format="mp3")
            
            # --- Clean up full audio file ---
            self._secure_delete_file(full_audio_path)
            # --------------------------------

            # Update job stage to success
            with get_session() as session:
                job_stage = session.query(JobStage).filter_by(
                    job_id=job_id, stage_name='download_video'
                ).first()
                if job_stage:
                    job_stage.state = StageState.success
                    job_stage.finished_at = utcnow()
                    job_stage.output_path = str(trimmed_audio_path)
                    session.commit()
            self.console.print(f"Successfully processed job {job_id}.", style="green")
            time.sleep(2) # Added delay to show all output
        except Exception as e:
            self.console.print(f"Error processing job {job_id}: {e}", style="red")
            with get_session() as session:
                job_stage = session.query(JobStage).filter_by(
                    job_id=job_id, stage_name='download_video'
                ).first()
                if job_stage:
                    job_stage.state = StageState.failed
                    job_stage.finished_at = utcnow()
                    job_stage.last_error = str(e)
                    session.commit()

                    # Optionally, run yt-dlp debug if it was a download error
                    if "yt-dlp" in str(e): # Heuristic to check if yt-dlp was the source of error
                        self.console.print("Attempting yt-dlp debug for more details...", style="yellow")
                        dbg_cmd = [
                            "yt-dlp",
                            "-v",
                            job_package.get('video_url'),
                            "-o", str(full_audio_path).replace('.mp3', '')
                        ]
                        try:
                            dbg = subprocess.run(dbg_cmd, capture_output=True, text=True, check=True)
                            self.console.print(f"yt-dlp debug output:\n{dbg.stdout}", style="yellow")
                            if dbg.stderr:
                                self.console.print(f"yt-dlp debug errors:\n{dbg.stderr}", style="red")
                        except subprocess.CalledProcessError as dbg_e:
                            self.console.print(f"yt-dlp debug command failed: {dbg_e}", style="red")
                            self.console.print(f"Stderr: {dbg_e.stderr}", style="red")
                        except Exception as inner_e:
                            self.console.print(f"An unexpected error occurred during yt-dlp debug: {inner_e}", style="red")
            time.sleep(2) # Added delay to show all output

    def _secure_delete_file(self, file_path: Path):
        """
        Securely deletes a file using the 'shred' command.
        """
        if not file_path.exists():
            self.console.print(f"File not found for secure deletion: {file_path}", style="yellow")
            return

        try:
            # -u: deallocate and remove after overwriting
            # -v: show progress
            # -z: add a final overwrite with zeros to hide shredding
            cmd = ["shred", "-uz", str(file_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.console.print(f"Securely deleted: {file_path}", style="yellow")
            if result.stdout:
                self.console.print(f"Shred stdout: {result.stdout}", style="dim")
            if result.stderr:
                self.console.print(f"Shred stderr: {result.stderr}", style="red")
        except FileNotFoundError:
            self.console.print(f"Shred command not found. Falling back to os.remove for {file_path}", style="red")
            try:
                os.remove(file_path)
                self.console.print(f"Insecurely deleted (shred not found): {file_path}", style="yellow")
            except OSError as e:
                self.console.print(f"Error falling back to os.remove for {file_path}: {e}", style="red")
        except subprocess.CalledProcessError as e:
            self.console.print(f"Error securely deleting {file_path} (shred failed): {e}", style="red")
            if e.stdout:
                self.console.print(f"Shred stdout: {e.stdout}", style="red")
            if e.stderr:
                self.console.print(f"Shred stderr: {e.stderr}", style="red")
        except Exception as e:
            self.console.print(f"An unexpected error occurred during secure deletion of {file_path}: {e}", style="red")
