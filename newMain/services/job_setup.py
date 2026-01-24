"""
This module provides services for ingesting video information into the database.
It defines functions to add new video entries and manage database sessions.
"""

import re
from datetime import datetime, timedelta
import yt_dlp

from rich.console import Console
from rich.prompt import Prompt

from database.session_manager import get_session
from database.models import VideoInfo, JobInfo, JobStage, StageState, STAGE_ORDER
from config.config import build_job_directory_path


class IngestLink:
    def __init__(self, data_packet):
        self.link = data_packet.get('link')
        self.start_seconds = data_packet.get('start_time')  # in seconds
        self.end_seconds  = data_packet.get('end_time')  # in seconds
        self.console = Console()

    def _extract_yt_id(self, url):
        """
        Extracts the YouTube video ID from a given URL.
        Supports standard, shortened, and embed URLs.
        """
        if not url:
            return None

        # Regex for standard, shortened, and embed YouTube URLs
        # Pattern explanation:
        # (?:https?://)? - Optional http or https
        # (?:www\.)? - Optional www.
        # (?:youtube\.com/(?:watch\?v=|embed/|v/)|youtu\.be/) - Domain and path for different URL types
        # ([a-zA-Z0-9_-]{11}) - The 11-character YouTube video ID
        youtube_regex = (
            r'(?:https?://)?(?:www\.)?'
            r'(?:youtube\.com/(?:watch\?v=|embed/|v/)|youtu\.be/)'
            r'([a-zA-Z0-9_-]{11})'
        )
        match = re.search(youtube_regex, url)
        if match:
            return match.group(1)
        return None

    def _get_video_metadata(self, url):
        """
        Fetches video metadata using yt-dlp without downloading the video.
        
        Returns:
            dict: A dictionary containing the video's metadata.
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'simulate': True,  # Do not download the video
            'force_generic_extractor': False, # Use appropriate extractor
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info_dict = ydl.extract_info(url, download=False)
                
                video_details = {
                    'yt_id': info_dict.get('id'),
                    'title': info_dict.get('title'),
                    'uploader': info_dict.get('uploader'),
                    'channel_id': info_dict.get('channel_id'),
                    'channel_url': info_dict.get('channel_url'),
                    'upload_date': info_dict.get('upload_date'),
                    'duration': info_dict.get('duration'),
                    'webpage_url': info_dict.get('webpage_url'),
                    'description': info_dict.get('description'),
                    'thumbnail': info_dict.get('thumbnail'),
                    'was_live': info_dict.get('was_live'),
                    'live_status': info_dict.get('live_status'),
                }
                return video_details
            
            except yt_dlp.utils.DownloadError as e:
                self.console.print(f"[red]Error fetching metadata for {url}: {e}[/red]")
                return {}

    def ingest_into_db(self):
        """
        Ingests the video link information and job details into the database.
        """
        yt_id = self._extract_yt_id(self.link)
        if not yt_id:
            self.console.print("[red]Error: Invalid YouTube URL provided.[/red]")
            return  # maybe return something to let the program know this failed

        with get_session() as session:
            try:
                # Find or create VideoInfo entry
                video_info = session.query(VideoInfo).filter_by(yt_id=yt_id).first()
                if not video_info:
                    self.console.print(f"[green]Fetching metadata for {self.link}...[/green]")
                    metadata = self._get_video_metadata(self.link)
                    
                    if not metadata:
                        self.console.print(f"[red]Failed to fetch metadata for {self.link}. Aborting ingestion.[/red]")
                        return
                    
                    video_info = VideoInfo(
                        yt_id=metadata.get('yt_id'),
                        title=metadata.get('title'),
                        uploader=metadata.get('uploader'),
                        channel_id=metadata.get('channel_id'),
                        channel_url=metadata.get('channel_url'),
                        upload_date=metadata.get('upload_date'),
                        duration=metadata.get('duration'),
                        webpage_url=metadata.get('webpage_url'),
                        description=metadata.get('description'),
                        thumbnail=metadata.get('thumbnail'),
                        was_live=metadata.get('was_live'),
                        live_status=metadata.get('live_status'),
                    )
                    session.add(video_info)
                    session.flush() # Ensure video_info gets an ID before JobInfo is created
                    self.console.print(f"[green]New VideoInfo created for YT ID: {yt_id}[/green]")
                else:
                    self.console.print(f"[green]Found existing VideoInfo for YT ID: {yt_id}[/green]")

                # Create JobInfo entry
                new_job = JobInfo(
                    video_id=video_info.id,
                    audio_start_time=self.start_seconds,
                    audio_end_time=self.end_seconds
                )
                session.add(new_job)
                session.flush() # Ensure new_job gets an ID before JobStages are created
                
                new_job.job_directory = build_job_directory_path(new_job.job_ulid, new_job.id)
                self.console.print(f"[green]New JobInfo created for Video ID {video_info.id} with Job ID {new_job.id}. Directory: {new_job.job_directory}[/green]")

                # Create JobStage entries for the new job
                for stage_name in STAGE_ORDER:
                    job_stage = JobStage(
                        job_id=new_job.id,
                        stage_name=stage_name,
                        state=StageState.pending # All new stages start as pending
                    )
                    session.add(job_stage)
                self.console.print(f"[green]Job stages created for Job ID {new_job.id}[/green]")

                session.commit()
                self.console.print(f"[bold green]Successfully ingested job for {self.link} (Job ID: {new_job.id})[/bold green]")
            except Exception as e:
                # no need for session.rollback, it's already handled in the context manager
                self.console.print(f"[red]Error ingesting job: {e}[/red]")

class ManualJobSetup:
    """Handles the setup of a single job provided manually."""
    def __init__(self):
        self.console = Console()

    def run(self):
        """The main execution method for the manual job setup flow."""
        console = self.console
        console.clear()
        console.rule("[bold yellow]Service: ManualJobSetup is running.[/bold yellow]")
        
        solicit_input = True
        while solicit_input:
            link = Prompt.ask("Enter YouTube URL")
            # Ask for start and end times in a flexible format (HH:MM:SS, MM:SS, or SS)
            start_time_str = Prompt.ask("Enter start time (HH:MM:SS, MM:SS, or SS)", default="0")
            end_time_str = Prompt.ask("Enter end time (HH:MM:SS, MM:SS, or SS)", default="0")

            # convert the input time to seconds
            start_seconds = self._parse_time_to_seconds(start_time_str)
            end_seconds = self._parse_time_to_seconds(end_time_str)

            if start_seconds is None or end_seconds is None:
                console.print("[red]Error: Invalid time format. Please use HH:MM:SS, MM:SS, or SS.[/red]")
                continue # Re-prompt the user

            # Basic validation: end time should not be before start time
            if end_seconds < start_seconds:
                console.print("[red]Error: End time cannot be before start time. Please re-enter.[/red]")
                continue # Re-prompt the user
            
            data_packet = {
                'link': link,
                'start_time': start_seconds,
                'end_time': end_seconds
                }
            
            solicit_input = False # Exit loop if inputs are valid

        ingestor = IngestLink(data_packet)
        ingestor.ingest_into_db()
    
    def _parse_time_to_seconds(self, time_str):
        """
        Parses a time string (HH:MM:SS, MM:SS, or SS) into total seconds.
        Returns None if parsing fails.
        """
        if not time_str:
            return 0 # An empty string or None can be interpreted as 0 seconds

        try:
            parts = [int(p) for p in time_str.split(':')]
            if len(parts) == 3:  # HH:MM:SS
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            elif len(parts) == 2:  # MM:SS
                return parts[0] * 60 + parts[1]
            elif len(parts) == 1:  # SS
                return parts[0]
            else:
                return None # Invalid number of parts
        except ValueError:
            return None # Failed to convert to int

class CsvJobSetup:
    """Handles the setup of jobs from a CSV file."""
    def __init__(self):
        self.console = Console()

    def run(self):
        """The main execution method for the CSV job setup flow."""
        self.console.print("[bold yellow]Service: CsvJobSetup is running.[/bold yellow]")
        # Placeholder for future logic (e.g., prompt for file path, process it)
        pass
