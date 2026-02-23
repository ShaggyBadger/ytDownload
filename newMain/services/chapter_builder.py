import json
import logging
import math  # Import math for word count calculations
from datetime import datetime
from pathlib import Path
import re  # Import the regular expression module

from joshlib.ollama import OllamaClient
from joshlib.gemini import GeminiClient  # Import GeminiClient
from rich.console import Console
from rich.prompt import Confirm  # Explicitly import Confirm for use
from sqlalchemy.orm import (
    joinedload,
)  # Import joinedload for eager loading relationships

from database.session_manager import get_session
from database.models import (
    JobInfo,
    JobStage,
    StageState,
    VideoInfo,
)  # Import VideoInfo for job.video relationship
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
        self.ollama_client = OllamaClient(
            model="llama3.2:3b", num_ctx=32768, temperature=0.1
        )
        self.gemini_client = (
            GeminiClient()
        )  # Instantiate Gemini Client for chapter polishing
        # Define the base directory for prompts relative to the current file
        self.PROMPTS_DIR = Path(__file__).resolve().parent / "prompts/chapter_builder"
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
        text = re.sub(r"\[\.\.\.\]", "", text)
        logger.debug("Removed '[...]' patterns.")

        # Replace multiple newlines with a single newline
        text = re.sub(r"\n\n+", "\n", text)
        logger.debug("Reduced multiple newlines to single newlines.")
        return text

    def run_final_polish(
        self, initial_text: str, thesis: str, tone: str, outline: str, summary: str
    ) -> str:
        """
        Manages the iterative "final pass" LLM polishing process.
        It repeatedly sends the text to the LLM, compares word counts,
        and asks for user approval before proceeding. After approval,
        it runs two evaluation prompts and asks for final sign-off.

        Args:
            initial_text (str): The text to be polished.

        Returns:
            str: The final polished and approved text, or the initial text if
                 the user does not approve.
        """
        logger.info("Initiating final polish stage for chapter.")
        polished_text = initial_text
        retry_count = 0
        MAX_RETRIES = 3

        final_pass_prompt_path = self.PROMPTS_DIR / "final-pass.txt"
        if not final_pass_prompt_path.exists():
            logger.error(f"Final pass prompt not found at {final_pass_prompt_path}.")
            self.console.print(
                f"[red]LLM prompt missing: {final_pass_prompt_path}[/red]"
            )
            return initial_text
        final_pass_prompt_template = final_pass_prompt_path.read_text()

        while retry_count < MAX_RETRIES:
            self.console.print(
                f"\n[bold yellow]--- Final Polishing Pass (Attempt {retry_count + 1}/{MAX_RETRIES}) ---[/bold yellow]"
            )
            initial_word_count = len(initial_text.split())
            self.console.print(f"Initial word count: {initial_word_count}")

            # Send text to LLM for final polish
            with self.console.status(
                "[bold green]Sending text for final polish...[/bold green]",
                spinner=config.SPINNER,
            ):
                prompt = final_pass_prompt_template.format(
                    TEXT_TO_POLISH=polished_text,
                    TONE=tone,
                    THESIS=thesis,
                    OUTLINE=outline,
                )

                polished_response = None
                # --- Attempt Gemini first ---
                try:
                    logger.info("Attempting final polish with Gemini client.")
                    gemini_response = self.gemini_client.submit_prompt(prompt)
                    if gemini_response.ok:
                        polished_response = gemini_response.output
                        logger.info("Gemini client successfully polished text.")
                    else:
                        logger.warning(
                            f"Gemini client failed to polish text (Error Type: {gemini_response.error_type}, Message: {gemini_response.error_message}). Falling back to Ollama."
                        )
                except Exception as e:
                    logger.error(
                        f"Gemini client encountered an unexpected error during final polish: {e}. Falling back to Ollama.",
                        exc_info=True,
                    )

                # --- Fallback to Ollama if Gemini failed or had an error ---
                if polished_response is None:
                    try:
                        logger.info(
                            "Attempting final polish with Ollama client (fallback)."
                        )
                        ollama_response = self.ollama_client.submit_prompt(prompt)
                        if ollama_response.ok:
                            polished_response = ollama_response.output
                            logger.info(
                                "Ollama client successfully polished text (fallback)."
                            )
                        else:
                            logger.error(
                                f"Ollama client also failed to polish text (Error Type: {ollama_response.error_type}, Message: {ollama_response.error_message})."
                            )
                            # If both fail, use the original text for this iteration to avoid crashing
                            polished_response = polished_text
                    except Exception as e:
                        logger.error(
                            f"Ollama client encountered an unexpected error during final polish (fallback): {e}.",
                            exc_info=True,
                        )
                        polished_response = (
                            polished_text  # Fallback to original if Ollama also errors
                        )

                llm_output = polished_response

            polished_text = llm_output
            current_word_count = len(polished_text.split())
            self.console.print(f"Polished word count: {current_word_count}")

            word_count_diff = abs(initial_word_count - current_word_count)
            # Calculate percentage difference, avoid division by zero
            percentage_diff = (
                (word_count_diff / initial_word_count) * 100
                if initial_word_count > 0
                else 0
            )

            self.console.print(
                f"Word count difference: {word_count_diff} ({percentage_diff:.2f}%)"
            )

            if Confirm.ask(
                "[bold blue]Are you satisfied with the word count and polishing?[/bold blue]"
            ):
                logger.info(
                    f"User approved final polish for Job ID {self.job_id} after {retry_count + 1} attempts."
                )
                break
            else:
                retry_count += 1
                logger.warning(
                    f"User declined final polish. Retrying. Attempt {retry_count}/{MAX_RETRIES}"
                )
                if retry_count == MAX_RETRIES:
                    self.console.print(
                        "[red]Max retries reached for final polish. Proceeding with last polished version.[/red]"
                    )
                else:
                    self.console.print("[yellow]Retrying final polish...[/yellow]")

        if retry_count == MAX_RETRIES and not Confirm.ask(
            "[bold red]Proceed with the current polished text despite not being satisfied with word count?[/bold red]"
        ):
            logger.info("User chose not to proceed after max retries for final polish.")
            return initial_text  # Return original text if not approved after max retries and explicit denial

        # --- Run evaluation prompts ---
        self.console.print(
            "\n[bold yellow]--- Running Final Evaluation Prompts ---[/bold yellow]"
        )

        fidelity_prompt_path = self.PROMPTS_DIR / "fidelity-and-drift-eval.txt"
        publication_audit_prompt_path = (
            self.PROMPTS_DIR / "publication-readiness-audit.txt"
        )

        if (
            not fidelity_prompt_path.exists()
            or not publication_audit_prompt_path.exists()
        ):
            logger.error("One or both evaluation prompt files are missing.")
            self.console.print(
                "[red]Missing evaluation prompt files. Skipping final evaluations.[/red]"
            )
            return self._clean_text(polished_text)  # Still return cleaned polished text

        fidelity_prompt_template = fidelity_prompt_path.read_text()
        publication_audit_prompt_template = publication_audit_prompt_path.read_text()

        evaluation_reports = {}
        with self.console.status(
            "[bold green]Generating fidelity and publication readiness reports...[/bold green]",
            spinner=config.SPINNER,
        ):
            # Fidelity and Drift Evaluation
            fidelity_prompt = fidelity_prompt_template.format(
                ORIGINAL_SERMON=initial_text, POLISHED_SERMON=polished_text
            )
            fidelity_response = self.ollama_client.submit_prompt(fidelity_prompt)
            evaluation_reports["fidelity"] = fidelity_response.output
            logger.debug("Fidelity evaluation report generated.")

            # Publication Readiness Audit
            publication_audit_prompt = publication_audit_prompt_template.format(
                SERMON_TEXT=polished_text,
                TONE=tone,
                THESIS=thesis,
                SUMMARY=summary,
                OUTLINE=outline,
            )
            publication_audit_response = self.ollama_client.submit_prompt(
                publication_audit_prompt
            )
            evaluation_reports["publication_audit"] = publication_audit_response.output
            logger.debug("Publication readiness audit report generated.")

        self.console.print(
            "\n[bold yellow]--- Fidelity and Drift Evaluation ---[/bold yellow]"
        )
        self.console.print(evaluation_reports["fidelity"])
        self.console.print(
            "\n[bold yellow]--- Publication Readiness Audit ---[/bold yellow]"
        )
        self.console.print(evaluation_reports["publication_audit"])
        self.console.print(
            "[bold yellow]-------------------------------------[/bold yellow]\n"
        )

        # Add a pause here to ensure the user has time to read the reports
        Confirm.ask(
            "[bold blue]Press Enter to review the evaluations and proceed to final approval.[/bold blue]"
        )

        if Confirm.ask(
            "[bold blue]Do you approve the final version based on these evaluations?[/bold blue]"
        ):
            logger.info(f"User gave final sign-off for Job ID {self.job_id}.")
            return self._clean_text(polished_text)
        else:
            logger.info(
                f"User declined final sign-off for Job ID {self.job_id}. Returning initial text."
            )
            self.console.print(
                "[red]Final sign-off declined. The chapter will not be built with the polished version.[/red]"
            )
            return initial_text

    def build_chapter_document(self):
        """
        Orchestrates the process of building the final chapter document.

        This method performs the following steps:
        1. Fetches job information from the database.
        2. Loads previously generated metadata (title, thesis, summary) from `metadata.json`.
        3. Loads edited paragraph content from `paragraphs.json`.
        4. Validates that all paragraphs have been edited.
        5. Assembles the final document content, including title, upload date, thesis, summary, and edited sermon text.
        6. **NEW**: Sends the assembled document to `run_final_polish` for iterative LLM refinement and user approval.
        7. If approved, saves the final chapter document to a file.
        8. Updates the 'build_chapter' stage in the database to reflect success or failure.
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
            tone = metadata.get(
                "speaker_tone", "neutral"
            )  # Assuming 'speaker_tone' from previous contexts
            outline = metadata.get("outline", "No outline provided.")
            logger.debug(
                f"Extracted from metadata: Title='{title}', Thesis='{thesis[:50]}...', Summary='{summary[:50]}...', Tone='{tone}', Outline='{outline[:50]}...'"
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

            # --- Send to final polish LLM and get user approval ---
            final_sermon_text = self.run_final_polish(
                initial_text=cleaned_content,
                thesis=thesis,
                tone=tone,
                outline=outline,
                summary=summary,
            )

            # If the user declined the final sign-off, we stop here.
            if final_sermon_text == cleaned_content and not Confirm.ask(
                "[bold red]User declined final sign-off. Do you still want to save the chapter with the initial cleaned text?[/bold red]"
            ):
                logger.info(
                    f"Chapter build cancelled by user for Job ID {self.job_id} after declining final sign-off."
                )
                self.console.print("[red]Chapter build cancelled.[/red]")
                return

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
            final_document_content += (
                f"Sermon\n"  # Placeholder section title for the main text
            )
            final_document_content += final_sermon_text
            logger.debug("Final document content assembled.")

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
                session.commit()  # Commit the changes to the database.
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
            self.console.print(
                f"[red]LLM prompt template missing: {prompt_template_path}[/red]"
            )
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
            self.console.print(
                f"[red]Error communicating with Ollama for evaluation. Check logs.[/red]"
            )
            return None
