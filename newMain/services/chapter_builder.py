import json
import logging
from datetime import datetime
from pathlib import Path
from joshlib.ollama import OllamaClient

from rich.console import Console

from database.session_manager import get_session
from database.models import JobInfo, JobStage, StageState
from config import config

logger = logging.getLogger(__name__)


class ChapterBuilder:
    """Class to handle building the final chapter document."""

    def __init__(self, job_id):
        """Initializes the ChapterBuilder for a specific job."""
        self.job_id = job_id
        self.console = Console()
        self.ollama_client = OllamaClient(model="llama3.2:3b", temperature=0.1)
        logger.debug(f"ChapterBuilder initialized for Job ID: {self.job_id}")

    def build_chapter_document(self):
        """
        Builds the final chapter document from metadata and edited paragraphs.
        """
        logger.info(f"Starting to build chapter document for Job ID: {self.job_id}")
        with get_session() as session:
            job = session.query(JobInfo).filter(JobInfo.id == self.job_id).first()
            if not job:
                logger.error(
                    f"Job with ID {self.job_id} not found in the database. Aborting chapter build."
                )
                self.console.print(f"[red]Job with ID {self.job_id} not found.[/red]")
                return

            job_directory = Path(job.job_directory)
            logger.debug(f"Job directory for Job ID {self.job_id}: {job_directory}")

            # --- Load Metadata ---
            metadata_path = job_directory / config.METADATA_FILE_NAME
            metadata = {}
            logger.debug(f"Attempting to load metadata from {metadata_path}")
            if metadata_path.exists():
                try:
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                    logger.info(f"Successfully loaded metadata from {metadata_path}.")
                except Exception:
                    logger.error(
                        f"Error loading or parsing metadata from {metadata_path}.",
                        exc_info=True,
                    )
                    self.console.print(
                        f"[red]Error loading metadata from {metadata_path}. Check logs.[/red]"
                    )
                    return
            else:
                logger.error(
                    f"Metadata file not found for Job ID {job.job_ulid} at {metadata_path}. Aborting chapter build."
                )
                self.console.print(
                    f"[red]Metadata file not found for job {job.job_ulid}.[/red]"
                )
                return

            title = metadata.get("title", "Untitled Chapter")
            thesis = metadata.get("thesis", "No thesis provided.")
            summary = metadata.get("summary", "No summary provided.")
            logger.debug(
                f"Extracted from metadata: Title='{title}', Thesis='{thesis[:50]}...', Summary='{summary[:50]}...'"
            )

            # --- Load Edited Paragraphs ---
            paragraph_json_path = job_directory / config.PARAGRAPHS_FILE_NAME
            paragraphs_data = []
            logger.debug(
                f"Attempting to load edited paragraphs from {paragraph_json_path}"
            )
            if paragraph_json_path.exists():
                try:
                    with open(paragraph_json_path, "r") as f:
                        paragraphs_data = json.load(f)
                    logger.info(
                        f"Successfully loaded {len(paragraphs_data)} paragraphs from {paragraph_json_path}."
                    )
                except Exception:
                    logger.error(
                        f"Error loading or parsing paragraphs from {paragraph_json_path}.",
                        exc_info=True,
                    )
                    self.console.print(
                        f"[red]Error loading paragraphs from {paragraph_json_path}. Check logs.[/red]"
                    )
                    return
            else:
                logger.error(
                    f"Paragraphs JSON file not found for Job ID {job.job_ulid} at {paragraph_json_path}. Aborting chapter build."
                )
                self.console.print(
                    f"[red]Paragraphs JSON file not found for job {job.job_ulid}.[/red]"
                )
                return

            # Ensure all paragraphs are edited before proceeding
            if any(p.get("edited") is None for p in paragraphs_data):
                logger.error(
                    f"Not all paragraphs for Job ID {job.job_ulid} are edited. Aborting chapter build."
                )
                self.console.print(
                    f"[red]Not all paragraphs for job {job.job_ulid} are edited. Cannot build chapter.[/red]"
                )
                return
            logger.debug("All paragraphs confirmed to be edited.")

            edited_content = "\n".join(
                [p["edited"] for p in paragraphs_data if p.get("edited")]
            )
            logger.debug("Combined all edited paragraph content.")

            # --- Construct Final Document ---
            final_document_content = f"{title}\n"
            logger.debug(f"Initial document content with title: '{title}'")

            # Add upload date if available
            if job.video and job.video.upload_date:
                try:
                    upload_date_obj = datetime.strptime(job.video.upload_date, "%Y%m%d")
                    formatted_date = upload_date_obj.strftime("%d %B, %Y")
                    final_document_content += f"{formatted_date}\n"
                    logger.debug(
                        f"Formatted upload date '{job.video.upload_date}' to '{formatted_date}'."
                    )
                except ValueError:
                    logger.warning(
                        f"Could not parse upload date '{job.video.upload_date}' for Job ID {self.job_id}. Using raw date string.",
                        exc_info=True,
                    )
                    final_document_content += f"Upload Date: {job.video.upload_date}\n"
            else:
                logger.debug(f"No video or upload_date found for Job ID {self.job_id}.")

            final_document_content += f"Thesis: {thesis}\n"
            final_document_content += f"Summary: {summary}\n"
            final_document_content += f"Sermon\n"  # Placeholder section title
            final_document_content += edited_content
            logger.debug("Final document content assembled.")

            # --- Save Final Document ---
            final_document_path = job_directory / config.FINAL_DOCUMENT_NAME
            logger.info(
                f"Attempting to save final chapter document to {final_document_path}"
            )
            try:
                with open(final_document_path, "w") as f:
                    f.write(final_document_content)
                logger.info(
                    f"Successfully built and saved chapter document at {final_document_path}."
                )
                self.console.print(
                    f"[green]Successfully built chapter document at {final_document_path}[/green]"
                )
            except Exception:
                logger.error(
                    f"Error saving final document to {final_document_path}.",
                    exc_info=True,
                )
                self.console.print(
                    f"[red]Error saving final document to {final_document_path}. Check logs.[/red]"
                )
                return

            # --- Update Database Stage ---
            build_chapter_stage = (
                session.query(JobStage)
                .filter_by(job_id=self.job_id, stage_name="build_chapter")
                .first()
            )

            if build_chapter_stage:
                build_chapter_stage.output_path = str(final_document_path)
                build_chapter_stage.state = StageState.success
                session.commit()
                logger.info(
                    f"Job ID {self.job_id}: 'build_chapter' stage marked as SUCCESS with output path: {final_document_path}."
                )
                self.console.print(
                    f"[green]Job {job.job_ulid}: 'build_chapter' stage marked as SUCCESS.[/green]"
                )
            else:
                logger.warning(
                    f"Job ID {job.job_ulid}: 'build_chapter' stage not found in database. Cannot update its state."
                )
                self.console.print(
                    f"[yellow]Job {job.job_ulid}: 'build_chapter' stage not found in database.[/red]"
                )

    def evaluate_chapter(self):
        pass
