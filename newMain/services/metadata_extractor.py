import json
import logging
from pathlib import Path
from typing import Dict, Any

from joshlib.gemini import GeminiClient
from rich.console import Console

from config import config
from database.models import JobInfo, JobStage, StageState
from database.session_manager import get_session

logger = logging.getLogger(__name__)

class MetadataExtractor:
    """
    This class handles the metadata extraction for a given job.
    It fetches job details, generates metadata for missing categories
    using an LLM (Ollama), saves it as a JSON file, and updates the job stage accordingly.
    """
    def __init__(self, job_id: int):
        self.job_id = job_id
        self.console = Console()
        self.prompts_dir = Path(__file__).parent / 'prompts' / 'metadata'
        self.llm_client = GeminiClient()
        logger.debug(f"MetadataExtractor initialized for Job ID: {self.job_id}. Prompts from: {self.prompts_dir}")

    def _load_metadata_json(self, metadata_path: Path) -> Dict[str, Any]:
        """Loads the metadata JSON file."""
        logger.debug(f"Attempting to load metadata from {metadata_path}.")
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                logger.debug(f"Successfully loaded metadata from {metadata_path}.")
                return metadata
            except json.JSONDecodeError:
                logger.error(f"Error decoding JSON from {metadata_path}.", exc_info=True)
                self.console.print(f"[red]Error decoding JSON from {metadata_path}. Check logs.[/red]")
            except Exception:
                logger.error(f"Error loading metadata from {metadata_path}.", exc_info=True)
                self.console.print(f"[red]Error loading metadata from {metadata_path}. Check logs.[/red]")
        else:
            logger.debug(f"Metadata file not found at {metadata_path}. Returning empty dict.")
        return {}

    def _save_metadata_json(self, metadata: Dict[str, Any], metadata_path: Path):
        """Saves the metadata JSON file."""
        logger.debug(f"Saving metadata to {metadata_path}.")
        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=4)
            logger.debug(f"Successfully saved metadata to {metadata_path}.")
        except Exception:
            logger.error(f"Error saving metadata to {metadata_path}.", exc_info=True)
            self.console.print(f"[red]Error saving metadata to {metadata_path}. Check logs.[/red]")

    def _initialize_metadata_json(self, job_directory: Path, metadata_path: Path):
        """
        Ensures the metadata.json file exists in the job directory with
        null values for all METADATA_CATEGORIES if not already present.
        """
        logger.debug(f"Initializing metadata.json at {metadata_path} for Job ID: {self.job_id}.")
        metadata = self._load_metadata_json(metadata_path)
        
        updated = False
        for category in config.METADATA_CATEGORIES:
            if category not in metadata or metadata[category] is None:
                metadata[category] = None
                updated = True
                logger.debug(f"Metadata category '{category}' was missing or null, initialized to None.")
        
        if updated or not metadata_path.exists():
            self._save_metadata_json(metadata, metadata_path)
            self.console.print(f"[green]Initialized metadata.json at {metadata_path}[/green]")
            logger.info(f"metadata.json at {metadata_path} ensured/initialized.")
        else:
            logger.debug("No changes needed during metadata.json initialization.")

    def _get_transcript_text(self, session, job_id: int) -> str:
        """Retrieves the formatted transcript text for a given job."""
        logger.debug(f"Retrieving formatted transcript text for Job ID: {job_id}.")
        formatted_transcript_stage = session.query(JobStage).filter_by(
            job_id=job_id,
            stage_name="format_gemini"
        ).first()

        if not formatted_transcript_stage or formatted_transcript_stage.state != StageState.success or not formatted_transcript_stage.output_path:
            logger.error(f"Formatted transcript not found or not successful for Job ID {job_id}. Stage output_path: {formatted_transcript_stage.output_path if formatted_transcript_stage else 'N/A'}")
            raise FileNotFoundError(f"Formatted transcript not found or not successful for Job ID {job_id}")

        formatted_transcript_path = Path(formatted_transcript_stage.output_path)
        if not formatted_transcript_path.is_file():
            logger.error(f"Formatted transcript file not found at {formatted_transcript_path} for Job ID {job_id}.")
            raise FileNotFoundError(f"Formatted transcript file not found at {formatted_transcript_path} for Job ID {job_id}")
        
        with open(formatted_transcript_path, 'r') as f:
            text = f.read()
            logger.debug(f"Successfully read formatted transcript from {formatted_transcript_path} (length: {len(text)}).")
            return text

    # --- Metadata Generation Methods ---
    def _generate_title(self, transcript_text: str, current_metadata: dict) -> str:
        logger.debug(f"Generating 'title' for Job ID: {self.job_id} using LLM.")
        prompt_path = self.prompts_dir / 'generate-title.txt'
        prompt_template = prompt_path.read_text()
        prompt = prompt_template.format(SERMON_TEXT=transcript_text)

        result = self.llm_client.submit_prompt(prompt)
        return result

    def _generate_thesis(self, transcript_text: str, current_metadata: dict) -> str:
        logger.debug(f"Generating 'thesis' for Job ID: {self.job_id} using LLM.")
        prompt_path = self.prompts_dir / 'generate-thesis.txt'
        prompt_template = prompt_path.read_text()
        prompt = prompt_template.format(SERMON_TEXT=transcript_text)
        return self.llm_client.submit_prompt(prompt)

    def _generate_summary(self, transcript_text: str, current_metadata: dict) -> str:
        logger.debug(f"Generating 'summary' for Job ID: {self.job_id} using LLM.")
        prompt_path = self.prompts_dir / 'generate-summary.txt'
        prompt_template = prompt_path.read_text()
        prompt = prompt_template.format(SERMON_TEXT=transcript_text)
        return self.llm_client.submit_prompt(prompt)

    def _generate_outline(self, transcript_text: str, current_metadata: dict) -> str:
        logger.debug(f"Generating 'outline' for Job ID: {self.job_id} using LLM.")
        prompt_path = self.prompts_dir / 'generate-outline.txt'
        prompt_template = prompt_path.read_text()
        prompt = prompt_template.format(SERMON_TEXT=transcript_text)
        return self.llm_client.submit_prompt(prompt)

    def _generate_tone(self, transcript_text: str, current_metadata: dict) -> str:
        logger.debug(f"Generating 'tone' for Job ID: {self.job_id} using LLM.")
        prompt_path = self.prompts_dir / 'generate-tone.txt'
        prompt_template = prompt_path.read_text()
        prompt = prompt_template.format(SERMON_TEXT=transcript_text)
        return self.llm_client.submit_prompt(prompt)

    # Main orchestration method
    def process_metadata(self):
        logger.info(f"Starting metadata processing for Job ID: {self.job_id}.")
        try:
            with get_session() as session:
                job = session.query(JobInfo).filter_by(id=self.job_id).first()
                if not job:
                    logger.error(f"Job with ID {self.job_id} not found in the database. Aborting metadata processing.")
                    self.console.print(f"[red]Job with ID {self.job_id} not found.[/red]")
                    return

                job_directory = Path(job.job_directory)
                metadata_path = job_directory / config.METADATA_FILE_NAME
                logger.debug(f"Job directory: {job_directory}, Metadata path: {metadata_path}")
                
                self._initialize_metadata_json(job_directory, metadata_path)
                
                transcript_text = ""
                try:
                    transcript_text = self._get_transcript_text(session, self.job_id)
                except FileNotFoundError as e:
                    logger.error(f"Could not retrieve transcript text for Job ID {self.job_id}: {e}", exc_info=True)
                    self.console.print(f"[red]Could not retrieve transcript for Job ID {self.job_id}. Aborting.[/red]")
                    return

                metadata = self._load_metadata_json(metadata_path)
                if not metadata:
                    logger.critical(f"Failed to load metadata from {metadata_path} after initialization. Aborting.")
                    self.console.print(f"[red]Failed to load metadata from {metadata_path} after initialization. Aborting.[/red]")
                    return

                all_categories_filled = True
                for category in config.METADATA_CATEGORIES:
                    if metadata.get(category) is None:
                        all_categories_filled = False
                        logger.info(f"Generating missing metadata: {category} for Job ID: {self.job_id}.")
                        self.console.print(f"[yellow]Generating missing metadata: {category}[/yellow]")
                        
                        generation_method_name = f"_generate_{category}"
                        generation_method = getattr(self, generation_method_name, None)

                        if generation_method:
                            status_message = f"Generating {category} for job {job.job_ulid}..."
                            with self.console.status(status_message, spinner=config.SPINNER):
                                try:
                                    gemini_result = generation_method(transcript_text, metadata)
                                    if gemini_result.ok is True:
                                        metadata[category] = gemini_result.output
                                        self._save_metadata_json(metadata, metadata_path)
                                        self.console.print(f"[green]  {category} generated and saved.[/green]")
                                        logger.info(f"Successfully generated and saved '{category}' for Job ID: {self.job_id}.")
                                    else:
                                        error_type = gemini_result.error_type
                                        error_message = gemini_result.error_message
                                        exit_code = gemini_result.exit_code

                                        logger.error(f'\n**********\nError with Gemini call.\nError type: {error_type}\nError Message: {error_message}\nExit Code: {exit_code}\n*********\n')
                                        break
                                except Exception:
                                    logger.error(f"Error generating '{category}' for Job ID: {self.job_id}.", exc_info=True)
                                    self.console.print(f"[red]  Error generating {category}. Check logs.[/red]")
                                    metadata[category] = f"[ERROR] - See logs" # Mark as error
                                    self._save_metadata_json(metadata, metadata_path) # Save error state
                                    all_categories_filled = False # Still not fully filled due to error
                        else:
                            logger.error(f"Generation method for category '{category}' not found in MetadataExtractor.", exc_info=True)
                            self.console.print(f"[red]  Error: Generation method for {category} not found.[/red]")
                            all_categories_filled = False # Cannot fill

                if all_categories_filled:
                    metadata_stage = session.query(JobStage).filter_by(
                        job_id=self.job_id,
                        stage_name="extract_metadata"
                    ).first()
                    if metadata_stage and metadata_stage.state != StageState.success:
                        metadata_stage.state = StageState.success
                        session.add(metadata_stage)
                        session.commit()
                        self.console.print(f"[green]Job {job.job_ulid}: 'extract_metadata' stage marked as SUCCESS.[/green]")
                        logger.info(f"Job ID {job.job_ulid}: 'extract_metadata' stage marked as SUCCESS in the database.")
                    else:
                        logger.debug(f"Job ID {job.job_ulid}: 'extract_metadata' stage was already successful or not found.")
                else:
                    logger.warning(f"Job ID {job.job_ulid}: Not all metadata categories filled. 'extract_metadata' stage remains pending/failed.")
                    self.console.print(f"[yellow]Job {job.job_ulid}: Not all metadata categories filled. 'extract_metadata' stage remains pending/failed.[/yellow]")
        except Exception:
            logger.critical(f"A critical error occurred during metadata processing for Job ID: {self.job_id}.", exc_info=True)
            self.console.print(f"[bold red]A critical error occurred during metadata processing for Job ID {self.job_id}. Check logs for details.[/bold red]")