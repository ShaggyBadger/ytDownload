import json
import logging
from datetime import datetime
from pathlib import Path
import re # Import the regular expression module
from joshlib.ollama import OllamaClient

from rich.console import Console
from rich.prompt import Confirm
from sqlalchemy.orm import joinedload # Import joinedload for eager loading relationships

from database.session_manager import get_session
from database.models import JobInfo, JobStage, StageState, VideoInfo  # Import VideoInfo for job.video relationship
from config import config

logger = logging.getLogger(__name__)


class ChapterBuilder:
    """
    Handles the final stage of the sermon processing pipeline: building the complete
    chapter document. This involves gathering metadata and edited paragraph content,
    sending the compiled text to an LLM (Ollama) for final evaluation, and then
    saving the chapter if the evaluation is satisfactory.
    """

    def __init__(self, job_id: int):
        """
        Initializes the ChapterBuilder for a specific job.

        Args:
            job_id (int): The database ID of the job for which to build the chapter.
        """
        self.job_id = job_id
        self.console = Console()
        # Initialize Ollama client for LLM interaction, using a specific model and temperature.
        # This client is used for the final evaluation of the generated chapter.
        self.ollama_client = OllamaClient(model="llama3.2:3b", temperature=0.1)
        logger.debug(f"ChapterBuilder initialized for Job ID: {self.job_id}")

    def _clean_text(self, text: str) -> str:
        """
        Applies a series of cleaning steps to the text:
        - Removes instances of `[...]`.
        - Replaces multiple consecutive newline characters with a single newline.

        Args:
            text (str): The input text to clean.

        Returns:
            str: The cleaned text.
        """
        logger.debug("Applying cleaning to text.")
        # Remove literal '[...]' patterns
        text = re.sub(r'\[\.\.\.\]', '', text)
        logger.debug("Removed '[...]' patterns.")

        # Replace multiple newlines with a single newline
        text = re.sub(r'\n\n+', '\n', text)
        logger.debug("Reduced multiple newlines to single newlines.")
        return text

    def build_chapter_document(self):
        """
        Orchestrates the process of building the final chapter document.

        This method performs the following steps:
        1. Fetches job information from the database.
        2. Loads previously generated metadata (title, thesis, summary) from `metadata.json`.
        3. Loads edited paragraph content from `paragraphs.json`.
        4. Validates that all paragraphs have been edited.
        5. Assembles the final document content, including title, upload date, thesis, summary, and edited sermon text.
        6. Sends the assembled document to an Ollama LLM for a final quality evaluation.
        7. Displays the LLM's evaluation report to the user and prompts for confirmation to save.
        8. If confirmed, saves the final chapter document to a file.
        9. Updates the 'build_chapter' stage in the database to reflect success or failure.
        """
        logger.info(f"Starting to build chapter document for Job ID: {self.job_id}")
        with get_session() as session:
            # Retrieve the job and its associated video information from the database.
            # The .options(joinedload(JobInfo.video)) ensures that video data is
            # loaded eagerly, preventing N+1 query problems later.
            job = (
                session.query(JobInfo)
                .options(joinedload(JobInfo.video))
                .filter(JobInfo.id == self.job_id)
                .first()
            )
            if not job:
                logger.error(
                    f"Job with ID {self.job_id} not found in the database. Aborting chapter build."
                )
                self.console.print(f"[red]Job with ID {self.job_id} not found.[/red]")
                return

            job_directory = Path(job.job_directory)
            logger.debug(f"Job directory for Job ID {self.job_id}: {job_directory}")

            # --- Load Metadata ---
            # The metadata file contains key information like title, thesis, and summary.
            metadata_path = job_directory / config.METADATA_FILE_NAME
            metadata = {}
            logger.debug(f"Attempting to load metadata from {metadata_path}")
            if metadata_path.exists():
                try:
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                    logger.info(f"Successfully loaded metadata from {metadata_path}.")
                except json.JSONDecodeError:
                    logger.error(
                        f"Error parsing metadata JSON from {metadata_path}. File might be corrupted.",
                        exc_info=True,
                    )
                    self.console.print(
                        f"[red]Error parsing metadata from {metadata_path}. Check logs.[/red]"
                    )
                    return
                except Exception:
                    logger.error(
                        f"An unexpected error occurred loading metadata from {metadata_path}.",
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
                    f"[red]Metadata file not found for job {job.job_ulid}. Aborting chapter build.[/red]"
                )
                return

            title = metadata.get("title", "Untitled Chapter")
            thesis = metadata.get("thesis", "No thesis provided.")
            summary = metadata.get("summary", "No summary provided.")
            logger.debug(
                f"Extracted from metadata: Title='{title}', Thesis='{thesis[:50]}...', Summary='{summary[:50]}...'"
            )

            # --- Load Edited Paragraphs ---
            # The paragraphs JSON file contains the text segmented into paragraphs,
            # with each paragraph having an 'edited' field after LLM processing.
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
                except json.JSONDecodeError:
                    logger.error(
                        f"Error parsing paragraphs JSON from {paragraph_json_path}. File might be corrupted.",
                        exc_info=True,
                    )
                    self.console.print(
                        f"[red]Error parsing paragraphs from {paragraph_json_path}. Check logs.[/red]"
                    )
                    return
                except Exception:
                    logger.error(
                        f"An unexpected error occurred loading paragraphs from {paragraph_json_path}.",
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
                    f"[red]Paragraphs JSON file not found for job {job.job_ulid}. Aborting chapter build.[/red]"
                )
                return

            # Ensure all paragraphs are edited before proceeding.
            # If any paragraph's 'edited' field is None, it means the LLM editing
            # stage was not fully completed for this job.
            if any(p.get("edited") is None for p in paragraphs_data):
                logger.error(
                    f"Not all paragraphs for Job ID {job.job_ulid} are edited. Aborting chapter build."
                )
                self.console.print(
                    f"[red]Not all paragraphs for job {job.job_ulid} are edited. Cannot build chapter.[/red]"
                )
                return
            logger.debug("All paragraphs confirmed to be edited.")

            # Combine all edited paragraph content into a single string.
            edited_content = "\n".join(
                [p["edited"] for p in paragraphs_data if p.get("edited")]
            )
            logger.debug("Combined all edited paragraph content.")

            # --- Clean combined content ---
            # Apply regex-based cleaning to remove unwanted patterns and excessive newlines.
            cleaned_content = self._clean_text(edited_content)
            logger.debug("Cleaned combined paragraph content.")

            # --- Construct Final Document ---
            # Assemble the various components into the final chapter document string.
            final_document_content = f"{title}\n"
            logger.debug(f"Initial document content with title: '{title}'")

            # Add upload date if available, formatting it nicely.
            if job.video and job.video.upload_date:
                try:
                    upload_date_obj = datetime.strptime(job.video.upload_date, "%Y%m%d")
                    formatted_date = upload_date_obj.strftime("%d %B, %Y")
                    final_document_content += f"{formatted_date}\n"
                    logger.debug(
                        f"Formatted upload date '{job.video.upload_date}' to '{formatted_date}'."
                    )
                except ValueError:
                    # Fallback if date parsing fails.
                    logger.warning(
                        f"Could not parse upload date '{job.video.upload_date}' for Job ID {self.job_id}. Using raw date string.",
                        exc_info=True,
                    )
                    final_document_content += f"Upload Date: {job.video.upload_date}\n"
            else:
                logger.debug(
                    f"No video or upload_date found for Job ID {self.job_id}. Skipping date addition."
                )

            # Add thesis, summary, and the main sermon content.
            final_document_content += f"Thesis: {thesis}\n"
            final_document_content += f"Summary: {summary}\n"
            final_document_content += f"Sermon\n"  # Placeholder section title for the main text
            final_document_content += cleaned_content
            logger.debug("Final document content assembled.")

            # --- Send to Ollama for final evaluation ---
            logger.info("Sending final document content to Ollama for evaluation.")

            # Display a Rich spinner while the LLM is processing the evaluation.
            # This provides visual feedback to the user during potentially long-running operations.
            with self.console.status(
                "[bold green]Sending chapter to Ollama for evaluation...[/bold green]",
                spinner=config.SPINNER, # Use the configured spinner style
            ):
                evaluation_report = self.evaluate_chapter_with_llm(
                    final_document_content
                )

            # Process the LLM's evaluation report.
            if evaluation_report:
                self.console.print("\n[bold yellow]--- LLM Chapter Evaluation Report ---[/bold yellow]")
                self.console.print(evaluation_report)
                self.console.print("[bold yellow]-------------------------------------[/bold yellow]\n")

                # Ask the user for confirmation before saving the chapter based on the LLM report.
                if not self.confirm_chapter_save():
                    logger.info(f"User chose to cancel saving the chapter for Job ID {self.job_id}.")
                    self.console.print("[red]Chapter save cancelled by user.[/red]")
                    return

                # --- Save Final Document ---
                # Define the path for the final chapter document.
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
                # Update the 'build_chapter' stage in the database to reflect completion.
                build_chapter_stage = (
                    session.query(JobStage)
                    .filter_by(job_id=self.job_id, stage_name="build_chapter")
                    .first()
                )

                if build_chapter_stage:
                    build_chapter_stage.output_path = str(final_document_path)
                    build_chapter_stage.state = StageState.success
                    session.commit() # Commit the changes to the database.
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
                        f"[yellow]Job {job.job_ulid}: 'build_chapter' stage not found in database. Please verify database integrity.[/yellow]"
                    )

            else:
                logger.error(
                    f"Ollama evaluation failed or returned empty for Job ID {self.job_id}. Chapter document will not be saved."
                )
                self.console.print(
                    f"[red]Ollama evaluation failed or returned empty for job {job.job_ulid}. Chapter document not saved.[/red]"
                )

    def confirm_chapter_save(self) -> bool:
        """
        Prompts the user for confirmation to save the chapter after reviewing the LLM's evaluation report.

        Returns:
            bool: True if the user confirms saving, False otherwise.
        """
        # Importing Confirm here to avoid circular dependency if rich.prompt is imported at module level
        # and also imported by other modules that ChapterBuilder might depend on for logging or config.
        from rich.prompt import Confirm
        return Confirm.ask("Are you satisfied with the LLM report and want to save this chapter?")

    def evaluate_chapter_with_llm(self, sermon_text: str) -> str | None:
        """
        Sends the compiled chapter text to an Ollama LLM for evaluation.

        Args:
            sermon_text (str): The complete text of the chapter document to be evaluated.

        Returns:
            str | None: The LLM's evaluation report as a string if successful,
                        or None if an error occurs during the LLM interaction.
        """
        # Construct the path to the evaluation prompt template.
        BASE_DIR = Path(__file__).resolve().parent
        PROMPTS_DIR = BASE_DIR / "prompts/chapter_builder"

        # Load the prompt template for chapter evaluation.
        prompt_template_path = PROMPTS_DIR / "eval-chapter.txt"
        if not prompt_template_path.exists():
            logger.error(f"LLM prompt template not found at {prompt_template_path}.")
            self.console.print(f"[red]LLM prompt template missing: {prompt_template_path}[/red]")
            return None

        prompt = prompt_template_path.read_text()
        # Format the prompt with the actual sermon text.
        prompt = prompt.format(SERMON_TEXT=sermon_text)
        logger.debug("Ollama evaluation prompt formatted.")

        try:
            # Submit the prompt to the Ollama LLM and retrieve the response.
            response = self.ollama_client.submit_prompt(prompt)
            logger.debug(f"Ollama evaluation response received.")
            return response.output
        except Exception as e:
            logger.error(f"Error evaluating chapter with Ollama: {e}", exc_info=True)
            self.console.print(f"[red]Error communicating with Ollama for evaluation. Check logs.[/red]")
            return None