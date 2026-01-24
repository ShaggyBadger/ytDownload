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

from database.session_manager import get_session
from database.models import VideoInfo, JobInfo, JobStage, StageState, STAGE_ORDER
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
        pass
    
    def _build_available_jobs(self):
        """returns a list of dicts with job info"""
        with get_session() as session:
            # Query all jobs where the 'download_video' stage is in 'pending' state
            query = session.query(JobInfo)
            query = query.join(JobStage)
            query = query.filter(
                JobStage.stage_name == 'download_video',
                JobStage.state == 'pending'
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
        for i in job_package:
            print(f'{i}: {job_package.get(i)}')
        input()
        try:
            # --- HOOKS for yt-dlp ---
            def progress_hook(d):
                if d['status'] == 'downloading':
                    percent_str = d.get('_percent_str', '0.0%').strip()
                    speed_str = d.get('_speed_str', '0.0B/s').strip()
                    eta_str = d.get('_eta_str', '00:00').strip()
                if d['status'] == 'finished':
                    print("Download complete.")

            def postprocessor_hook(d):
                if d['status'] == 'started':
                    print(f"Post-processing: {d['postprocessor']}...")
                if d['status'] == 'finished':
                    print("Post-processing complete. Pausing for 2 seconds...")
                    time.sleep(2)
            # ------------------------

            # Download
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': str(config.FULL_MP3_NAME).replace('.mp3', ''), # yt-dlp adds the extension
                'keepvideo': False,
                'progress_hooks': [progress_hook],
                'postprocessor_hooks': [postprocessor_hook],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download([job_package.get('video_url')])
                except Exception as e:
                    # Run shell-level yt-dlp debug to get full FFmpeg logs
                    import subprocess
                    dbg_cmd = [
                        "yt-dlp",
                        "-v",
                        job_package.get('video_url'),
                        "-o", str(config.FULL_MP3_NAME).replace('.mp3', '')
                    ]
                    dbg = subprocess.run(dbg_cmd, capture_output=True, text=True)
                    raise

            # Trim
            trimmed_audio_path = job_package.get('job_dir') / config.MP3_SEGMENT_NAME
            
            audio = AudioSegment.from_file(job_package.get('video_url'))
            start_ms = job_package.get('audio_start_time') * 1000
            end_ms = job_package.get('audio_end_time') * 1000
            trimmed_audio = audio[start_ms:end_ms]

            trimmed_audio.export(trimmed_audio_path, format="mp3")

        except Exception as e:
            pass
