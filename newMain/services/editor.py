import json
import logging
import re
from pathlib import Path

from joshlib.ollama import OllamaClient
from rich.console import Console

from database.session_manager import get_session
from database.models import JobInfo, JobStage, StageState
from config import config

logger = logging.getLogger(__name__)


class Editor:
    """Class to handle paragraph editing using an Ollama-compatible API."""

    def __init__(self, job_id):
        """Initializes the editor for a specific job."""
        self.job_id = job_id
        self.console = Console()
        self.ollama_client = OllamaClient(temperature=0.15)
        logger.debug(f"Editor service initialized for Job ID: {self.job_id}")

    def _build_paragraphs_json_data(self, transcript_text, job_directory):
        """Builds the initial data structure for paragraphs.json."""
        logger.debug(f"Building paragraphs.json data for Job ID: {self.job_id}")
        BASE_DIR = Path(__file__).resolve().parent
        PROMPTS_DIR = BASE_DIR / "prompts/editor"
        logger.debug(f"Prompts directory set to: {PROMPTS_DIR}")

        speaker_tone = "neutral"
        metadata_path = Path(job_directory) / config.METADATA_FILE_NAME
        if metadata_path.exists():
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                    speaker_tone = metadata.get("tone", "neutral")
                logger.info(
                    f"Successfully read speaker tone '{speaker_tone}' from {metadata_path}"
                )
            except Exception:
                logger.error(
                    f"Error reading or parsing {metadata_path} to get speaker tone.",
                    exc_info=True,
                )
        else:
            logger.warning(
                f"Metadata file not found at {metadata_path}. Using default speaker tone: '{speaker_tone}'."
            )

        paragraphs = [p.strip() for p in re.split(r"\n+", transcript_text) if p.strip()]
        total_paragraphs = len(paragraphs)
        logger.info(f"Split transcript into {total_paragraphs} paragraphs.")

        paragraphs_data = []
        for i, paragraph in enumerate(paragraphs):
            prompt_template_path = None
            try:
                if i == 0 and total_paragraphs > 1:
                    prompt_template_path = PROMPTS_DIR / "edit-paragraph-first.txt"
                elif i == total_paragraphs - 1 and total_paragraphs > 1:
                    prompt_template_path = PROMPTS_DIR / "edit-paragraph-last.txt"
                else:
                    prompt_template_path = PROMPTS_DIR / "edit-paragraph-standard.txt"

                logger.debug(
                    f"Using prompt template: {prompt_template_path.name} for paragraph {i+1}/{total_paragraphs}"
                )
                prompt_template = prompt_template_path.read_text()

                # Format the prompt based on paragraph position
                if i == 0 and total_paragraphs > 1:
                    prompt = prompt_template.format(
                        SPEAKER_TONE=speaker_tone,
                        PARAGRAPH_TARGET=paragraph,
                        PARAGRAPH_NEXT=paragraphs[i + 1],
                    )
                elif i == total_paragraphs - 1 and total_paragraphs > 1:
                    prompt = prompt_template.format(
                        SPEAKER_TONE=speaker_tone,
                        PARAGRAPH_TARGET=paragraph,
                        PARAGRAPH_PREV=paragraphs[i - 1],
                    )
                elif total_paragraphs > 1:
                    prompt = prompt_template.format(
                        SPEAKER_TONE=speaker_tone,
                        PARAGRAPH_TARGET=paragraph,
                        PARAGRAPH_PREV=paragraphs[i - 1],
                        PARAGRAPH_NEXT=paragraphs[i + 1],
                    )
                else:  # Handle case with only one paragraph
                    prompt = prompt_template.format(
                        SPEAKER_TONE=speaker_tone,
                        PARAGRAPH_TARGET=paragraph,
                        PARAGRAPH_NEXT="",
                    )

                paragraphs_data.append(
                    {
                        "index": i,
                        "original": paragraph,
                        "prompt": prompt,
                        "edited": None,
                    }
                )

            except FileNotFoundError:
                logger.error(
                    f"Prompt file not found: {prompt_template_path}", exc_info=True
                )
                paragraphs_data.append(
                    {
                        "index": i,
                        "original": paragraph,
                        "prompt": "[PROMPT FILE NOT FOUND]",
                        "edited": None,
                    }
                )
            except Exception:
                logger.error(f"Error creating prompt for paragraph {i}", exc_info=True)
                paragraphs_data.append(
                    {
                        "index": i,
                        "original": paragraph,
                        "prompt": "[ERROR CREATING PROMPT]",
                        "edited": None,
                    }
                )

        return paragraphs_data

    def _save_paragraphs_to_file(self, data, file_path):
        """Saves the paragraph data to the JSON file."""
        logger.debug(f"Saving paragraph data to {file_path}")
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception:
            logger.error(f"Error saving paragraph data to {file_path}", exc_info=True)

    def _load_paragraphs_from_file(self, file_path):
        """Loads paragraph data from a JSON file."""
        logger.debug(f"Loading paragraphs from {file_path}")
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Paragraphs JSON file not found at {file_path}")
            return None
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {file_path}", exc_info=True)
            return None
        except Exception:
            logger.error(
                f"An unexpected error occurred loading paragraphs from {file_path}",
                exc_info=True,
            )
            return None

    def _get_paragraph_file_path(self, job_directory):
        """Returns the path for the paragraphs.json file."""
        path = Path(job_directory) / config.PARAGRAPHS_FILE_NAME
        logger.debug(f"Paragraph file path determined to be: {path}")
        return path

    def run_editor(self):
        """Orchestrates the sermon editing process (initial JSON creation)."""
        logger.info(f"Running editor (JSON creation) for Job ID: {self.job_id}")
        with get_session() as session:
            job = session.query(JobInfo).filter(JobInfo.id == self.job_id).first()
            if not job:
                logger.error(f"Job with ID {self.job_id} not found in the database.")
                return

            format_gemini_stage = (
                session.query(JobStage)
                .filter_by(job_id=self.job_id, stage_name="format_gemini")
                .first()
            )
            if not format_gemini_stage or not format_gemini_stage.output_path:
                logger.warning(
                    f"Formatted transcript path not found in 'format_gemini' stage for Job ID: {self.job_id}. Cannot create paragraphs.json."
                )
                return

            transcript_path = Path(format_gemini_stage.output_path)
            if not transcript_path.exists():
                logger.error(
                    f"Transcript file not found at the path specified in the database: {transcript_path}"
                )
                return

            paragraph_file_path = self._get_paragraph_file_path(job.job_directory)
            if paragraph_file_path.exists():
                logger.info(
                    f"Paragraphs JSON file already exists at {paragraph_file_path}. Skipping creation."
                )
            else:
                logger.info("Paragraphs JSON file not found. Creating...")
                transcript_text = transcript_path.read_text()
                paragraphs_data = self._build_paragraphs_json_data(
                    transcript_text, job.job_directory
                )
                self._save_paragraphs_to_file(paragraphs_data, paragraph_file_path)

                logger.debug(
                    f"Updating database for 'format_gemini' stage with path: {paragraph_file_path}"
                )
                format_gemini_stage.paragraph_json_path = str(paragraph_file_path)
                session.commit()
                logger.info(
                    f"Committed paragraph_json_path to database for Job ID: {self.job_id}"
                )

    def process_paragraphs_for_editing(self):
        """Loads paragraphs.json and sends unedited ones to the Ollama API."""
        logger.info(
            f"Starting paragraph-by-paragraph editing for Job ID: {self.job_id}"
        )
        with get_session() as session:
            job = session.query(JobInfo).filter(JobInfo.id == self.job_id).first()
            if not job:
                logger.error(f"Job with ID {self.job_id} not found.")
                return

            paragraph_file_path = self._get_paragraph_file_path(job.job_directory)
            if not paragraph_file_path.exists():
                logger.error(
                    f"Paragraphs JSON file not found at {paragraph_file_path}. Cannot perform editing."
                )
                return

            paragraphs_data = self._load_paragraphs_from_file(paragraph_file_path)
            if paragraphs_data is None:
                logger.error("Failed to load paragraph data. Aborting editing process.")
                return

            total_paragraphs = len(paragraphs_data)
            edited_this_run = 0

            for i, p_entry in enumerate(paragraphs_data):
                if p_entry.get("edited") is None or p_entry.get("edited") == "[ERROR] - See logs for details.":
                    status_message = f"Processing paragraph {i+1}/{total_paragraphs} for Job ID {self.job_id}..."
                    logger.info(status_message)
                    with self.console.status(status_message, spinner=config.SPINNER):
                        try:
                            ollama_response = self.ollama_client.submit_prompt(
                                p_entry["prompt"]
                            )
                            logger.debug(
                                f"Ollama response for paragraph {i+1}: '{ollama_response[:100]}...'"
                            )
                            p_entry["edited"] = ollama_response
                            edited_this_run += 1
                            self._save_paragraphs_to_file(
                                paragraphs_data, paragraph_file_path
                            )  # Save after each successful edit
                        except Exception as e:
                            logger.error(
                                f"Error processing paragraph {i+1} for Job ID {self.job_id} with Ollama.",
                                exc_info=True,
                            )
                            p_entry["edited"] = f"[ERROR] - See logs for details."
                            self._save_paragraphs_to_file(
                                paragraphs_data, paragraph_file_path
                            )  # Save error state
                else:
                    logger.debug(
                        f"Paragraph {i+1}/{total_paragraphs} already edited. Skipping."
                    )

            if edited_this_run == 0:
                logger.info(
                    f"No new paragraphs required editing for Job ID {self.job_id}."
                )
            else:
                logger.info(
                    f"Finished editing {edited_this_run} paragraphs for Job ID {self.job_id}."
                )

            if all(p.get("edited") is not None for p in paragraphs_data):
                logger.info(
                    f"All {total_paragraphs} paragraphs for Job ID {self.job_id} are now edited."
                )
                edit_llm_stage = (
                    session.query(JobStage)
                    .filter_by(job_id=self.job_id, stage_name="edit_local_llm")
                    .first()
                )
                if edit_llm_stage and edit_llm_stage.state != StageState.success:
                    edit_llm_stage.state = StageState.success
                    session.commit()
                    self.console.print(
                        f"[green]Job {job.job_ulid}: 'edit_local_llm' stage marked as SUCCESS.[/green]"
                    )
                    logger.info(
                        f"Job ID {self.job_id}: 'edit_local_llm' stage marked as SUCCESS in the database."
                    )
            else:
                logger.warning(
                    f"Job ID {self.job_id}: Not all paragraphs are edited. 'edit_local_llm' stage remains pending."
                )

    def build_paragraph_editing_score(
        self, original_paragraph_dict, edited_paragraph_dict
    ):
        """Placeholder for comparing original and edited paragraphs."""
        logger.warning(
            "build_paragraph_editing_score is a placeholder and not yet implemented."
        )
        pass
