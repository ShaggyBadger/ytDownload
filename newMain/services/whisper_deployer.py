import requests
from pathlib import Path
from rich.console import Console
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_
from sqlalchemy import or_

from config import config
from database.session_manager import get_session
from database.models import JobInfo, JobStage, STAGE_ORDER, StageState

class Deployer:
    def __init__(self):
        self.console = Console()
        self.fastapi_base_url = config.FASTAPI_URL # Store the base URL

    def deploy_pending_jobs(self):
        with self.console.status("Searching for jobs to deploy...", spinner=config.SPINNER) as status:
            with get_session() as session:
                jobs_to_deploy = self._find_jobs_to_deploy(session)

                if not jobs_to_deploy:
                    status.update("No jobs are ready for deployment.", spinner=config.SPINNER)
                    self.console.print("No jobs are ready for deployment.", style="green")
                    return

                status.update(f"Found {len(jobs_to_deploy)} job(s) to deploy. Deploying...", spinner=config.SPINNER)
                for job in jobs_to_deploy:
                    self._deploy_job(session, job)

    def _find_jobs_to_deploy(self, session: Session):
        """
        Finds jobs where the 'extract_audio' stage is 'success' and the
        'transcribe_whisper' stage is 'pending'.
        """
        jobs = (
            session.query(JobInfo)
            .join(JobInfo.stages)
            .filter(
                JobStage.stage_name == "extract_audio",
                JobStage.state == StageState.success,
            )
            .filter(
                JobInfo.stages.any(
                    and_(
                        JobStage.stage_name == "transcribe_whisper",
                        or_(
                        JobStage.state == StageState.pending,
                        JobStage.state == StageState.failed
                        )
                    )
                )
            )
            .options(selectinload(JobInfo.stages))
            .all()
        )
        return jobs

    def _deploy_job(self, session: Session, job: JobInfo):
        with self.console.status(f"Deploying job [bold cyan]{job.job_ulid}[/bold cyan]...", spinner=config.SPINNER) as status:
            url = self.fastapi_base_url + "/new-job"

            # Dynamically construct the path to the audio segment
            audio_segment_path = Path(job.job_directory) / config.MP3_SEGMENT_NAME

            whisper_stage = None
            for stage in job.stages:
                if stage.stage_name == "transcribe_whisper":
                    whisper_stage = stage
                    break

            if not whisper_stage:
                status.stop()
                self.console.print(f"[red]Error: Could not find whisper stage for job {job.job_ulid}.[/red]")
                return

            file_path = audio_segment_path
            if not file_path.exists():
                status.stop()
                self.console.print(f"[red]Error: Audio file not found at {file_path} for job {job.job_ulid}.[/red]")
                whisper_stage.state = StageState.failed
                whisper_stage.last_error = f"File not found at {file_path}"
                session.commit()
                return
            
            try:
                status.update(f"Sending audio for job [bold cyan]{job.job_ulid}[/bold cyan] to the transcription server...")
                with open(file_path, 'rb') as f:
                    files = {'file': (file_path.name, f, 'audio/mpeg')}
                    data = {'whisper_model': 'large', 'ulid_': job.job_ulid}
                    response = requests.post(url, files=files, data=data, timeout=60)
                    response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
                    response_data = response.json()
                    
                    if response_data.get("status") == "deployed":
                        status.stop()
                        self.console.print(f"Successfully deployed job [bold green]{job.job_ulid}[/bold green] for transcription.", style="green")
                        whisper_stage.state = StageState.running
                        session.commit()
                    else:
                        status.stop()
                        raise requests.exceptions.HTTPError(f"Server returned non-deployed status: {response_data.get('status')}")
            except requests.exceptions.RequestException as e:
                status.stop()
                self.console.print(f"[red]Network error deploying job [bold cyan]{job.job_ulid}[/bold cyan]: {e}[/red]")
                whisper_stage.state = StageState.failed
                whisper_stage.last_error = str(e)
                session.commit()
            except Exception as e:
                status.stop()
                self.console.print(f"[bold red]An unexpected error occurred deploying job [bold cyan]{job.job_ulid}[/bold cyan]: {e}[/bold red]")
                whisper_stage.state = StageState.failed
                whisper_stage.last_error = str(e)
                session.commit()

    def check_for_completed_jobs(self):
        with self.console.status("Checking for completed transcription jobs...", spinner=config.SPINNER) as status:
            with get_session() as session:
                running_jobs = self._find_running_jobs(session)
                if not running_jobs:
                    status.update(
                        status = "No jobs are currently processing on the server.",
                        spinner=config.SPINNER,
                        )
                    self.console.print("No jobs are currently processing on the server.", style="green")
                    return
                
                status.update(f"Found {len(running_jobs)} job(s) being transcribed. Checking status...", spinner=config.SPINNER)
                for job in running_jobs:
                    self._check_and_retrieve_job(session, job)

    def recover_specific_job(self, job_ulid: str):
        with self.console.status(f"Attempting to manually recover job [bold cyan]{job_ulid}[/bold cyan]...", spinner=config.SPINNER) as status:
            with get_session() as session:
                job = self._find_job_by_ulid(session, job_ulid)
                if not job:
                    status.update(
                        status=f"Job [bold red]{job_ulid}[/bold red] not found in the local database.",
                        spinner=config.SPINNER
                    )
                    self.console.print(f"Job [bold red]{job_ulid}[/bold red] not found in the local database.", style="red")
                    return
                
                status.update(f"Found job [bold cyan]{job.job_ulid}[/bold cyan]. Checking server status...", spinner=config.SPINNER)
                self._check_and_retrieve_job(session, job)

    def _find_running_jobs(self, session: Session):
        """Finds jobs where the 'transcribe_whisper' stage is 'running'."""
        jobs = (
            session.query(JobInfo)
            .join(JobInfo.stages)
            .filter(
                JobStage.stage_name == "transcribe_whisper",
                JobStage.state == StageState.running,
            )
            .options(selectinload(JobInfo.stages))
            .all()
        )
        return jobs

    def _find_job_by_ulid(self, session: Session, job_ulid: str):
        """Finds a job by its ULID."""
        job = (
            session.query(JobInfo)
            .filter(JobInfo.job_ulid == job_ulid)
            .options(selectinload(JobInfo.stages))
            .first()
        )
        return job

    def _check_and_retrieve_job(self, session: Session, job: JobInfo):
        with self.console.status(f"Checking status for job [bold cyan]{job.job_ulid}[/bold cyan]...", spinner=config.SPINNER) as status:
            whisper_stage = next((s for s in job.stages if s.stage_name == "transcribe_whisper"), None)
            if not whisper_stage: 
                status.stop()
                self.console.print(f"[red]Error: No transcribe_whisper stage found for job [bold cyan]{job.job_ulid}[/bold cyan]. This indicates a pipeline issue.[/red]")
                return # Should not happen

            # 1. Check job status on the server first
            status_url = self.fastapi_base_url + f"/report-job-status/{job.job_ulid}"
            try:
                status.update(f"Requesting server status for job [bold cyan]{job.job_ulid}[/bold cyan]...")
                status_response = requests.get(status_url, timeout=10)
                status_response.raise_for_status()
                server_job_status = status_response.json().get("status")

                if server_job_status == "completed":
                    status.update(f"Server reports job [bold green]{job.job_ulid}[/bold green] as [bold green]completed[/bold green]. Retrieving transcript...")
                    self._retrieve_transcript(session, job, whisper_stage)
                    status.stop() # Stop status here as retrieve_transcript will handle its own status/messages
                elif server_job_status == "failed":
                    status.stop()
                    self.console.print(f"[red]Server reports job [bold cyan]{job.job_ulid}[/bold cyan] as [bold red]failed[/bold red]. Please check the remote server logs.[/red]")
                    whisper_stage.state = StageState.failed
                    whisper_stage.last_error = f"Remote server reported job as failed."
                    session.commit()
                else:
                    self.console.print(f"Job [bold cyan]{job.job_ulid}[/bold cyan] is still processing on server. Status: [yellow]{server_job_status}[/yellow]", style="yellow")

            except requests.exceptions.RequestException as e:
                status.stop()
                error_message = str(e.response.text if e.response else e)
                self.console.print(f"[red]Error checking status for job [bold cyan]{job.job_ulid}[/bold cyan]: {error_message}[/red]")
                whisper_stage.state = StageState.failed
                whisper_stage.last_error = f"Failed to check server status: {error_message}"
                session.commit()
            except Exception as e:
                status.stop()
                self.console.print(f"[bold red]An unexpected error occurred while checking status for job [bold cyan]{job.job_ulid}[/bold cyan]: {e}[/bold red]")
                whisper_stage.state = StageState.failed
                whisper_stage.last_error = f"Unexpected error during status check: {e}"
                session.commit()

    def _retrieve_transcript(self, session: Session, job: JobInfo, whisper_stage: JobStage):
        with self.console.status(f"Retrieving transcript for job [bold cyan]{job.job_ulid}[/bold cyan]...", spinner=config.SPINNER) as status:
            retrieve_url = self.fastapi_base_url + f"/retrieve-job/{job.job_ulid}"
            try:
                status.update(f"Downloading transcript from server for job [bold cyan]{job.job_ulid}[/bold cyan]...")
                response = requests.get(retrieve_url, timeout=60)
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                
                transcript_content = response.text
                transcript_filename = config.WHISPER_TRANSCRIPT_NAME
                transcript_path = Path(job.job_directory) / transcript_filename
                
                status.update(f"Saving transcript for job [bold cyan]{job.job_ulid}[/bold cyan] to [green]{transcript_path}[/green]...")
                with open(transcript_path, "w", encoding="utf-8") as f:
                    f.write(transcript_content)
                
                self.console.print(f"Success! Transcript for job [bold green]{job.job_ulid}[/bold green] saved to [green]{transcript_path}[/green]", style="green")
                
                whisper_stage.state = StageState.success
                whisper_stage.output_path = str(transcript_path)
                session.commit()

            except requests.exceptions.RequestException as e:
                self.console.print(f"[red]Error retrieving job [bold cyan]{job.job_ulid}[/bold cyan]: {e}[/red]")
                whisper_stage.state = StageState.failed
                whisper_stage.last_error = f"Failed to retrieve transcript: {e}"
                session.commit()
            except Exception as e:
                self.console.print(f"[bold red]An unexpected error occurred while retrieving job [bold cyan]{job.job_ulid}[/bold cyan]: {e}[/bold red]")
                whisper_stage.state = StageState.failed
                whisper_stage.last_error = f"Unexpected error during transcript retrieval: {e}"
                session.commit()
