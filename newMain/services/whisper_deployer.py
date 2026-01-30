import logging
import requests
from pathlib import Path
from rich.console import Console
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_
from sqlalchemy import or_

from config import config
from database.session_manager import get_session
from database.models import JobInfo, JobStage, STAGE_ORDER, StageState

logger = logging.getLogger(__name__)


class Deployer:
    def __init__(self):
        self.console = Console()
        self.fastapi_base_url = config.FASTAPI_URL
        logger.debug(
            f"Deployer service initialized. FastAPI URL: {self.fastapi_base_url}"
        )

    def deploy_pending_jobs(self):
        logger.info("Starting deployment of pending jobs.")
        with self.console.status(
            "Searching for jobs to deploy...", spinner=config.SPINNER
        ) as status:
            try:
                with get_session() as session:
                    jobs_to_deploy = self._find_jobs_to_deploy(session)

                    if not jobs_to_deploy:
                        status.update(
                            "No jobs are ready for deployment.", spinner=config.SPINNER
                        )
                        self.console.print(
                            "No jobs are ready for deployment.", style="green"
                        )
                        logger.info("No jobs found ready for deployment.")
                        return

                    status.update(
                        f"Found {len(jobs_to_deploy)} job(s) to deploy. Deploying...",
                        spinner=config.SPINNER,
                    )
                    logger.info(
                        f"Found {len(jobs_to_deploy)} job(s) ready for deployment."
                    )
                    for job in jobs_to_deploy:
                        try:
                            self._deploy_job(session, job)
                        except Exception as e:
                            logger.error(
                                f"Error deploying individual job {job.job_ulid}: {e}",
                                exc_info=True,
                            )
                            self.console.print(
                                f"[red]Error deploying job {job.job_ulid}. Check logs.[/red]"
                            )
            except Exception as e:
                logger.critical(
                    f"Critical error during deployment of pending jobs: {e}",
                    exc_info=True,
                )
                self.console.print(
                    f"[bold red]Critical error during deployment. Check logs for details.[/bold red]"
                )

    def _find_jobs_to_deploy(self, session: Session):
        logger.debug(
            "Querying for jobs ready for deployment (extract_audio success, transcribe_whisper pending/failed)."
        )
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
                            JobStage.state == StageState.failed,
                        ),
                    )
                )
            )
            .options(selectinload(JobInfo.stages))
            .all()
        )
        logger.debug(f"Found {len(jobs)} jobs ready for deployment.")
        return jobs

    def _deploy_job(self, session: Session, job: JobInfo):
        logger.info(
            f"Deploying job {job.id} (ULID: {job.job_ulid}) to transcription server."
        )
        with self.console.status(
            f"Deploying job [bold cyan]{job.job_ulid}[/bold cyan]...",
            spinner=config.SPINNER,
        ) as status:
            url = self.fastapi_base_url + "/new-job"
            logger.debug(f"Deployment target URL: {url}")

            audio_segment_path = Path(job.job_directory) / config.MP3_SEGMENT_NAME
            logger.debug(f"Audio segment path: {audio_segment_path}")

            whisper_stage = next(
                (s for s in job.stages if s.stage_name == "transcribe_whisper"), None
            )

            if not whisper_stage:
                status.stop()
                logger.error(
                    f"Error: Could not find whisper stage for job {job.job_ulid}. This indicates a pipeline configuration issue."
                )
                self.console.print(
                    f"[red]Error: Could not find whisper stage for job {job.job_ulid}.[/red]"
                )
                return

            file_path = audio_segment_path
            if not file_path.exists():
                status.stop()
                logger.error(
                    f"Error: Audio file not found at {file_path} for job {job.job_ulid}. Updating stage to FAILED."
                )
                self.console.print(
                    f"[red]Error: Audio file not found at {file_path} for job {job.job_ulid}.[/red]"
                )
                whisper_stage.state = StageState.failed
                whisper_stage.last_error = f"File not found at {file_path}"
                session.commit()
                return

            try:
                status.update(
                    f"Sending audio for job [bold cyan]{job.job_ulid}[/bold cyan] to the transcription server..."
                )
                logger.debug(f"Opening audio file {file_path} for transfer.")
                with open(file_path, "rb") as f:
                    files = {"file": (file_path.name, f, "audio/mpeg")}
                    data = {"whisper_model": "large", "ulid_": job.job_ulid}
                    logger.debug(
                        f"Sending POST request to {url} with ULID: {job.job_ulid}."
                    )
                    response = requests.post(url, files=files, data=data, timeout=60)
                    response.raise_for_status()
                    response_data = response.json()
                    logger.debug(f"Server response for deployment: {response_data}")

                    if response_data.get("status") == "deployed":
                        status.stop()
                        self.console.print(
                            f"Successfully deployed job [bold green]{job.job_ulid}[/bold green] for transcription.",
                            style="green",
                        )
                        whisper_stage.state = StageState.running
                        session.commit()
                        logger.info(
                            f"Job {job.job_ulid} successfully deployed and stage updated to RUNNING."
                        )
                    else:
                        status.stop()
                        logger.error(
                            f"Server returned non-deployed status for job {job.job_ulid}: {response_data.get('status')}. Marking stage as FAILED."
                        )
                        raise requests.exceptions.HTTPError(
                            f"Server returned non-deployed status: {response_data.get('status')}"
                        )
            except requests.exceptions.RequestException as e:
                status.stop()
                error_message = str(e.response.text if e.response else e)
                logger.error(
                    f"Network error deploying job {job.job_ulid}: {error_message}. Marking stage as FAILED.",
                    exc_info=True,
                )
                self.console.print(
                    f"[red]Network error deploying job [bold cyan]{job.job_ulid}[/bold cyan]: {e}[/red]"
                )
                whisper_stage.state = StageState.failed
                whisper_stage.last_error = f"Network error: {error_message}"
                session.commit()
            except Exception as e:
                status.stop()
                logger.critical(
                    f"An unexpected error occurred deploying job {job.job_ulid}: {e}. Marking stage as FAILED.",
                    exc_info=True,
                )
                self.console.print(
                    f"[bold red]An unexpected error occurred deploying job [bold cyan]{job.job_ulid}[/bold cyan]: {e}[/bold red]"
                )
                whisper_stage.state = StageState.failed
                whisper_stage.last_error = str(e)
                session.commit()

    def check_for_completed_jobs(self):
        logger.info("Starting check for completed transcription jobs.")
        with self.console.status(
            "Checking for completed transcription jobs...", spinner=config.SPINNER
        ) as status:
            try:
                with get_session() as session:
                    running_jobs = self._find_running_jobs(session)
                    if not running_jobs:
                        status.update(
                            "No jobs are currently processing on the server.",
                            spinner=config.SPINNER,
                        )
                        self.console.print(
                            "No jobs are currently processing on the server.",
                            style="green",
                        )
                        logger.info(
                            "No jobs found currently running for transcription."
                        )
                        return

                    status.update(
                        f"Found {len(running_jobs)} job(s) being transcribed. Checking status...",
                        spinner=config.SPINNER,
                    )
                    logger.info(
                        f"Found {len(running_jobs)} jobs with 'transcribe_whisper' stage RUNNING."
                    )
                    for job in running_jobs:
                        try:
                            self._check_and_retrieve_job(session, job)
                        except Exception as e:
                            logger.error(
                                f"Error checking/retrieving job {job.job_ulid}: {e}",
                                exc_info=True,
                            )
                            self.console.print(
                                f"[red]Error processing job {job.job_ulid}. Check logs.[/red]"
                            )
            except Exception as e:
                logger.critical(
                    f"Critical error during check for completed jobs: {e}",
                    exc_info=True,
                )
                self.console.print(
                    f"[bold red]Critical error during status check. Check logs for details.[/bold red]"
                )

    def recover_specific_job(self, job_ulid: str):
        logger.info(f"Attempting manual recovery for Job ULID: {job_ulid}.")
        with self.console.status(
            f"Attempting to manually recover job [bold cyan]{job_ulid}[/bold cyan]...",
            spinner=config.SPINNER,
        ) as status:
            try:
                with get_session() as session:
                    job = self._find_job_by_ulid(session, job_ulid)
                    if not job:
                        status.update(
                            f"Job [bold red]{job_ulid}[/bold red] not found in the local database.",
                            spinner=config.SPINNER,
                        )
                        self.console.print(
                            f"Job [bold red]{job_ulid}[/bold red] not found in the local database.",
                            style="red",
                        )
                        logger.warning(
                            f"Job ULID {job_ulid} not found in the local database for manual recovery."
                        )
                        return

                    status.update(
                        f"Found job [bold cyan]{job.job_ulid}[/bold cyan]. Checking server status...",
                        spinner=config.SPINNER,
                    )
                    logger.info(
                        f"Job {job.job_ulid} found in local DB. Proceeding to check server status."
                    )
                    self._check_and_retrieve_job(session, job)
            except Exception as e:
                logger.critical(
                    f"Critical error during manual recovery for Job ULID {job_ulid}: {e}",
                    exc_info=True,
                )
                self.console.print(
                    f"[bold red]Critical error during manual recovery. Check logs for details.[/bold red]"
                )

    def _find_running_jobs(self, session: Session):
        logger.debug("Querying for jobs with 'transcribe_whisper' stage RUNNING.")
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
        logger.debug(f"Found {len(jobs)} jobs with 'transcribe_whisper' stage RUNNING.")
        return jobs

    def _find_job_by_ulid(self, session: Session, job_ulid: str):
        logger.debug(f"Querying for JobInfo by ULID: {job_ulid}.")
        job = (
            session.query(JobInfo)
            .filter(JobInfo.job_ulid == job_ulid)
            .options(selectinload(JobInfo.stages))
            .first()
        )
        if job:
            logger.debug(f"Job {job_ulid} found in local database (ID: {job.id}).")
        else:
            logger.debug(f"Job {job_ulid} not found in local database.")
        return job

    def _check_and_retrieve_job(self, session: Session, job: JobInfo):
        logger.info(
            f"Checking server status and potentially retrieving for Job ULID: {job.job_ulid}."
        )
        with self.console.status(
            f"Checking status for job [bold cyan]{job.job_ulid}[/bold cyan]...",
            spinner=config.SPINNER,
        ) as status:
            whisper_stage = next(
                (s for s in job.stages if s.stage_name == "transcribe_whisper"), None
            )
            if not whisper_stage:
                status.stop()
                logger.error(
                    f"Error: No transcribe_whisper stage found for job {job.job_ulid}. This indicates a pipeline issue."
                )
                self.console.print(
                    f"[red]Error: No transcribe_whisper stage found for job [bold cyan]{job.job_ulid}[/bold cyan]. This indicates a pipeline issue.[/red]"
                )
                return

            status_url = self.fastapi_base_url + f"/report-job-status/{job.job_ulid}"
            try:
                status.update(
                    f"Requesting server status for job [bold cyan]{job.job_ulid}[/bold cyan] from {status_url}..."
                )
                logger.debug(
                    f"Requesting server status for job {job.job_ulid} from {status_url}."
                )
                status_response = requests.get(status_url, timeout=10)
                status_response.raise_for_status()
                server_job_status = status_response.json().get("status")
                logger.debug(
                    f"Server reported status for job {job.job_ulid}: {server_job_status}"
                )

                if server_job_status == "completed":
                    status.update(
                        f"Server reports job [bold green]{job.job_ulid}[/bold green] as [bold green]completed[/bold green]. Retrieving transcript..."
                    )
                    logger.info(
                        f"Server reports job {job.job_ulid} as COMPLETED. Initiating transcript retrieval."
                    )
                    self._retrieve_transcript(session, job, whisper_stage)
                    status.stop()
                elif server_job_status == "failed":
                    status.stop()
                    logger.error(
                        f"Server reports job {job.job_ulid} as FAILED. Updating stage to FAILED."
                    )
                    self.console.print(
                        f"[red]Server reports job [bold cyan]{job.job_ulid}[/bold cyan] as [bold red]failed[/bold red]. Please check the remote server logs.[/red]"
                    )
                    whisper_stage.state = StageState.failed
                    whisper_stage.last_error = f"Remote server reported job as failed."
                    session.commit()
                else:
                    self.console.print(
                        f"Job [bold cyan]{job.job_ulid}[/bold cyan] is still processing on server. Status: [yellow]{server_job_status}[/yellow]",
                        style="yellow",
                    )
                    logger.info(
                        f"Job {job.job_ulid} is still PROCESSING on server. Status: {server_job_status}."
                    )

            except requests.exceptions.RequestException as e:
                status.stop()
                error_message = str(e.response.text if e.response else e)
                logger.error(
                    f"Network error checking status for job {job.job_ulid}: {error_message}. Marking stage as FAILED.",
                    exc_info=True,
                )
                self.console.print(
                    f"[red]Error checking status for job [bold cyan]{job.job_ulid}[/bold cyan]: {error_message}[/red]"
                )
                whisper_stage.state = StageState.failed
                whisper_stage.last_error = (
                    f"Failed to check server status: {error_message}"
                )
                session.commit()
            except Exception as e:
                status.stop()
                logger.critical(
                    f"An unexpected error occurred while checking status for job {job.job_ulid}: {e}. Marking stage as FAILED.",
                    exc_info=True,
                )
                self.console.print(
                    f"[bold red]An unexpected error occurred while checking status for job [bold cyan]{job.job_ulid}[/bold cyan]: {e}[/bold red]"
                )
                whisper_stage.state = StageState.failed
                whisper_stage.last_error = f"Unexpected error during status check: {e}"
                session.commit()

    def _retrieve_transcript(
        self, session: Session, job: JobInfo, whisper_stage: JobStage
    ):
        logger.info(f"Retrieving transcript for Job ULID: {job.job_ulid}.")
        with self.console.status(
            f"Retrieving transcript for job [bold cyan]{job.job_ulid}[/bold cyan]...",
            spinner=config.SPINNER,
        ) as status:
            retrieve_url = self.fastapi_base_url + f"/retrieve-job/{job.job_ulid}"
            try:
                status.update(
                    f"Downloading transcript from server for job [bold cyan]{job.job_ulid}[/bold cyan] from {retrieve_url}..."
                )
                logger.debug(
                    f"Downloading transcript for job {job.job_ulid} from {retrieve_url}."
                )
                response = requests.get(retrieve_url, timeout=60)
                response.raise_for_status()

                transcript_content = response.text
                transcript_filename = config.WHISPER_TRANSCRIPT_NAME
                transcript_path = Path(job.job_directory) / transcript_filename

                status.update(
                    f"Saving transcript for job [bold cyan]{job.job_ulid}[/bold cyan] to [green]{transcript_path}[/green]..."
                )
                logger.debug(
                    f"Saving transcript content (length: {len(transcript_content)}) to {transcript_path}."
                )
                with open(transcript_path, "w", encoding="utf-8") as f:
                    f.write(transcript_content)

                self.console.print(
                    f"Success! Transcript for job [bold green]{job.job_ulid}[/bold green] saved to [green]{transcript_path}[/green]",
                    style="green",
                )
                logger.info(
                    f"Successfully saved transcript for job {job.job_ulid} to {transcript_path}."
                )

                whisper_stage.state = StageState.success
                whisper_stage.output_path = str(transcript_path)
                session.commit()
                logger.info(
                    f"Job {job.job_ulid}: 'transcribe_whisper' stage marked as SUCCESS with output path: {transcript_path}."
                )

            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Network error retrieving transcript for job {job.job_ulid}: {e}. Marking stage as FAILED.",
                    exc_info=True,
                )
                self.console.print(
                    f"[red]Error retrieving job [bold cyan]{job.job_ulid}[/bold cyan]: {e}[/red]"
                )
                whisper_stage.state = StageState.failed
                whisper_stage.last_error = f"Failed to retrieve transcript: {e}"
                session.commit()
            except Exception as e:
                logger.critical(
                    f"An unexpected error occurred while retrieving transcript for job {job.job_ulid}: {e}. Marking stage as FAILED.",
                    exc_info=True,
                )
                self.console.print(
                    f"[bold red]An unexpected error occurred while retrieving job [bold cyan]{job.job_ulid}[/bold cyan]: {e}[/bold red]"
                )
                whisper_stage.state = StageState.failed
                whisper_stage.last_error = (
                    f"Unexpected error during transcript retrieval: {e}"
                )
                session.commit()
