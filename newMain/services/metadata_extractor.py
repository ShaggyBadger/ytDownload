import json  # For working with JSON data (metadata files)
import logging  # For logging events and debugging information
from pathlib import Path  # For object-oriented filesystem paths
from typing import Dict, Any  # For type hinting, especially for dictionary structures

from joshlib.gemini import (
    GeminiClient,
)  # Custom client for interacting with the Gemini LLM
from joshlib.ollama import (
    OllamaClient,
)  # Custom client for interacting with the Ollama LLM

from rich.console import Console

from config import config  # Application configuration settings
from database.models import (
    JobInfo,
    JobStage,
    StageState,
)  # SQLAlchemy models for database interaction
from database.session_manager import get_session  # Utility to get a database session

# Initialize logger for this module
logger = logging.getLogger(__name__)


class MetadataExtractor:
    # ... (docstring remains as updated)

    def __init__(self, job_id: int):
        """
        Initializes the MetadataExtractor for a specific job.

        Args:
            job_id (int): The unique identifier for the job being processed.
        """
        self.job_id = job_id  # Store the job ID
        self.console = Console()  # Rich console instance for formatted output
        # Define the directory where LLM prompts for metadata generation are stored
        self.prompts_dir = Path(__file__).parent / "prompts" / "metadata"
        self.llm_client = GeminiClient()  # Instantiate the Gemini LLM client

        # instantiate the Ollama client with small model and higher context to
        # process long sermons
        self.ollama_client = OllamaClient(
            model="llama3.2:3b", temperature=0.2, num_ctx=32768
        )
        logger.debug(
            f"MetadataExtractor initialized for Job ID: {self.job_id}. Prompts from: {self.prompts_dir}"
        )

    def _load_metadata_json(self, metadata_path: Path) -> Dict[str, Any]:
        """
        Loads the metadata JSON file from the specified path.

        Args:
            metadata_path (Path): The filesystem path to the metadata JSON file.

        Returns:
            Dict[str, Any]: A dictionary containing the loaded metadata, or an empty dictionary
                            if the file does not exist or an error occurs during loading/parsing.
        """
        logger.debug(f"Attempting to load metadata from {metadata_path}.")
        if metadata_path.exists():
            try:
                with open(
                    metadata_path, "r", encoding="utf-8"
                ) as f:  # Ensure UTF-8 encoding
                    metadata = json.load(f)
                logger.debug(f"Successfully loaded metadata from {metadata_path}.")
                return metadata
            except json.JSONDecodeError:
                # Log JSON decoding errors, which indicate a malformed metadata file
                logger.error(
                    f"Error decoding JSON from {metadata_path}. The file might be corrupted or malformed.",
                    exc_info=True,
                )
                self.console.print(
                    f"[red]Error decoding JSON from {metadata_path}. Check logs for details.[/red]"
                )
            except Exception:
                # Catch any other potential errors during file reading
                logger.error(
                    f"An unexpected error occurred while loading metadata from {metadata_path}.",
                    exc_info=True,
                )
                self.console.print(
                    f"[red]Error loading metadata from {metadata_path}. Check logs for details.[/red]"
                )
        else:
            # If the metadata file doesn't exist, it's a normal scenario for initial processing
            logger.debug(
                f"Metadata file not found at {metadata_path}. Returning an empty dictionary for initialization."
            )
        return {}

    def _save_metadata_json(self, metadata: Dict[str, Any], metadata_path: Path):
        """
        Saves the provided metadata dictionary to a JSON file at the specified path.

        Args:
            metadata (Dict[str, Any]): The dictionary containing the metadata to save.
            metadata_path (Path): The filesystem path where the metadata JSON file should be saved.
        """
        logger.debug(f"Saving metadata to {metadata_path}.")
        try:
            with open(
                metadata_path, "w", encoding="utf-8"
            ) as f:  # Ensure UTF-8 encoding
                json.dump(
                    metadata, f, indent=4
                )  # Use indent for pretty-printing the JSON
            logger.debug(f"Successfully saved metadata to {metadata_path}.")
        except Exception:
            # Catch any errors during file writing
            logger.error(f"Error saving metadata to {metadata_path}.", exc_info=True)
            self.console.print(
                f"[red]Error saving metadata to {metadata_path}. Check logs for details.[/red]"
            )

    def _initialize_metadata_json(self, job_directory: Path, metadata_path: Path):
        """
        Ensures the `metadata.json` file exists in the job directory and is correctly structured.
        It initializes any missing metadata categories with `None` values based on `config.METADATA_CATEGORIES`.

        Args:
            job_directory (Path): The root directory for the current job.
            metadata_path (Path): The expected path to the metadata JSON file.
        """
        logger.debug(
            f"Initializing metadata.json at {metadata_path} for Job ID: {self.job_id}."
        )
        # Load existing metadata or an empty dictionary if not found/valid
        metadata = self._load_metadata_json(metadata_path)

        updated = (
            False  # Flag to track if any changes were made to the metadata dictionary
        )
        # Iterate through all defined metadata categories in the application configuration
        for category in config.METADATA_CATEGORIES:
            # If a category is not present in the loaded metadata or its value is None, initialize it
            if category not in metadata or metadata[category] is None:
                metadata[category] = None
                updated = True
                logger.debug(
                    f"Metadata category '{category}' was missing or null, initialized to None."
                )

        # If any categories were initialized or the file didn't exist initially, save the updated metadata
        if updated or not metadata_path.exists():
            self._save_metadata_json(metadata, metadata_path)
            self.console.print(
                f"[green]Initialized metadata.json at {metadata_path}[/green]"
            )
            logger.info(
                f"metadata.json at {metadata_path} ensured/initialized with all categories set to None if missing."
            )
        else:
            logger.debug(
                "No changes needed during metadata.json initialization as all categories are present and not None."
            )

    def _get_transcript_text(self, session, job_id: int) -> str:
        """
        Retrieves the formatted transcript text for a given job from the database
        and verifies its existence on the filesystem.

        Args:
            session: The SQLAlchemy session for database interaction.
            job_id (int): The ID of the job whose transcript is to be retrieved.

        Returns:
            str: The content of the formatted transcript file.

        Raises:
            FileNotFoundError: If the formatted transcript stage is not successful,
                                its output path is missing, or the file does not exist.
        """
        logger.debug(f"Retrieving formatted transcript text for Job ID: {job_id}.")
        # Query the database to find the 'format_gemini' stage for the current job
        formatted_transcript_stage = (
            session.query(JobStage)
            .filter_by(job_id=job_id, stage_name="format_gemini")
            .first()
        )

        # Validate if the stage exists, was successful, and has a recorded output path
        if (
            not formatted_transcript_stage  # Stage record not found
            or formatted_transcript_stage.state
            != StageState.success  # Stage was not successful
            or not formatted_transcript_stage.output_path  # Output path is not recorded
        ):
            error_msg = (
                f"Formatted transcript not found or not successful for Job ID {job_id}. "
                f"Stage output_path: {formatted_transcript_stage.output_path if formatted_transcript_stage else 'N/A'}"
            )
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # Construct the file path from the recorded output path in the database
        formatted_transcript_path = Path(formatted_transcript_stage.output_path)
        # Verify that the file actually exists on the filesystem
        if not formatted_transcript_path.is_file():
            error_msg = f"Formatted transcript file not found at {formatted_transcript_path} for Job ID {job_id}."
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # Read and return the content of the transcript file
        with open(
            formatted_transcript_path, "r", encoding="utf-8"
        ) as f:  # Ensure UTF-8 encoding
            text = f.read()
            logger.debug(
                f"Successfully read formatted transcript from {formatted_transcript_path} (length: {len(text)})."
            )
            return text

    # --- Metadata Generation Methods ---
    # Each _generate_<category> method is responsible for using the LLM to create specific metadata.
    # To add a new category, follow the steps outlined in the class docstring.

    def _generate_title(
        self, transcript_text: str, current_metadata: dict
    ) -> Any:  # Changed return type to Any
        """
        Generates a title for the sermon using the LLM based on the transcript text.

        Args:
            transcript_text (str): The full text of the formatted sermon transcript.
            current_metadata (dict): The current metadata dictionary (useful if generating
                                     a new category depends on previously generated ones).

        Returns:
            Any: The raw response object from the LLM client.
        """
        logger.debug(f"Generating 'title' for Job ID: {self.job_id} using LLM.")
        prompt_path = (
            self.prompts_dir / "generate-title.txt"
        )  # Path to the specific prompt file
        prompt_template = prompt_path.read_text(
            encoding="utf-8"
        )  # Load the prompt template
        # Format the prompt with the actual sermon text
        prompt = prompt_template.format(SERMON_TEXT=transcript_text)

        # Submit the formatted prompt to the Gemini LLM client
        result = self.llm_client.submit_prompt(prompt)
        return result

    def _generate_thesis(self, transcript_text: str, current_metadata: dict) -> Any:
        """
        Generates a thesis statement for the sermon using the LLM.
        (Refer to _generate_title for detailed comment structure, as the pattern is identical)
        """
        logger.debug(f"Generating 'thesis' for Job ID: {self.job_id} using LLM.")
        prompt_path = self.prompts_dir / "generate-thesis.txt"
        decicion_prompt_path = self.prompts_dir / "thesis-decision.txt"

        prompt_template = prompt_path.read_text(encoding="utf-8")
        decision_template = decicion_prompt_path.read_text(encoding="utf-8")

        prompt = prompt_template.format(SERMON_TEXT=transcript_text)

        r1_response = self.ollama_client.submit_prompt(prompt)
        if not r1_response.ok:
            logger.error(f"First thesis generation failed: {r1_response.error_message}")
            return r1_response  # Return the response object directly on failure
        r1 = r1_response.output
        logger.debug("First thesis generation complete...")

        r2_response = self.ollama_client.submit_prompt(prompt)
        if not r2_response.ok:
            logger.error(
                f"Second thesis generation failed: {r2_response.error_message}"
            )
            return r2_response  # Return the response object directly on failure
        r2 = r2_response.output
        logger.debug("Second thesis generation complete...")

        r3_response = self.ollama_client.submit_prompt(prompt)
        if not r3_response.ok:
            logger.error(f"Third thesis generation failed: {r3_response.error_message}")
            return r3_response  # Return the response object directly on failure
        r3 = r3_response.output
        logger.debug("Third thesis generation complete...")

        decision_prompt = decision_template.format(
            t1=r1, t2=r2, t3=r3, SERMON_TEXT=transcript_text
        )

        logger.debug("Submitting thesis decision prompt to LLM...")
        thesis_response = self.ollama_client.submit_prompt(decision_prompt)
        # Always return the thesis_response object for process_metadata to handle
        return thesis_response

    def _generate_summary(self, transcript_text: str, current_metadata: dict) -> Any:
        """
        Generates a summary for the sermon using the LLM.
        (Refer to _generate_title for detailed comment structure, as the pattern is identical)
        """
        logger.debug(f"Generating 'summary' for Job ID: {self.job_id} using LLM.")
        prompt_path = self.prompts_dir / "generate-summary.txt"
        prompt_template = prompt_path.read_text(encoding="utf-8")
        prompt = prompt_template.format(SERMON_TEXT=transcript_text)
        return self.ollama_client.submit_prompt(prompt)

    def _generate_outline(self, transcript_text: str, current_metadata: dict) -> Any:
        """
        Generates an outline for the sermon using the LLM.
        (Refer to _generate_title for detailed comment structure, as the pattern is identical)
        """
        logger.debug(f"Generating 'outline' for Job ID: {self.job_id} using LLM.")
        prompt_path = self.prompts_dir / "generate-outline.txt"
        prompt_template = prompt_path.read_text(encoding="utf-8")
        prompt = prompt_template.format(SERMON_TEXT=transcript_text)
        return self.ollama_client.submit_prompt(prompt)

    def _generate_tone(self, transcript_text: str, current_metadata: dict) -> Any:
        """
        Generates a description of the tone of the sermon using the LLM.
        (Refer to _generate_title for detailed comment structure, as the pattern is identical)
        """
        logger.debug(f"Generating 'tone' for Job ID: {self.job_id} using LLM.")
        prompt_path = self.prompts_dir / "generate-tone.txt"
        prompt_template = prompt_path.read_text(encoding="utf-8")
        prompt = prompt_template.format(SERMON_TEXT=transcript_text)
        return self.ollama_client.submit_prompt(prompt)

    def _generate_main_text(self, transcript_text: str, current_metadata: dict) -> Any:
        """
        Generates the main text content, potentially re-summarized or refined, using the LLM.
        (Refer to _generate_title for detailed comment structure, as the pattern is identical)
        """
        logger.debug(f"Generating 'main_text' for Job ID: {self.job_id} using LLM.")
        prompt_path = self.prompts_dir / "generate-main-text.txt"
        prompt_template = prompt_path.read_text(encoding="utf-8")
        prompt = prompt_template.format(SERMON_TEXT=transcript_text)
        return self.ollama_client.submit_prompt(prompt)

    # Main orchestration method
    def process_metadata(self) -> bool:
        """
        Orchestrates the entire metadata extraction process for the job.
        This method fetches job details, ensures the metadata JSON file is initialized,
        retrieves the formatted transcript, and then iteratively generates any missing
        metadata categories using the LLM. Finally, it updates the job stage status.

        Returns:
            bool: True if processing completed (or failed for a non-quota reason),
                  False if a Gemini quota error occurred and processing should stop.
        """
        logger.info(f"Starting metadata processing for Job ID: {self.job_id}.")
        try:
            # Establish a database session for the duration of this operation
            with get_session() as session:
                # Fetch the JobInfo record for the current job ID
                job = session.query(JobInfo).filter_by(id=self.job_id).first()
                if not job:
                    logger.error(
                        f"Job with ID {self.job_id} not found in the database. Aborting metadata processing."
                    )
                    self.console.print(
                        f"[red]Job with ID {self.job_id} not found.[/red]"
                    )
                    return True  # Not a quota error, just this job failed

                # Construct the path to the job's directory and the metadata file within it
                job_directory = Path(job.job_directory)
                metadata_path = job_directory / config.METADATA_FILE_NAME
                logger.debug(
                    f"Job directory: {job_directory}, Metadata path: {metadata_path}"
                )

                # Ensure the metadata.json file exists and is populated with all categories
                self._initialize_metadata_json(job_directory, metadata_path)

                transcript_text = ""
                try:
                    # Retrieve the formatted transcript text, which is the input for LLM generation
                    transcript_text = self._get_transcript_text(session, self.job_id)
                except FileNotFoundError as e:
                    # Handle cases where the transcript file is not found or stage was not successful
                    logger.error(
                        f"Could not retrieve transcript text for Job ID {self.job_id}: {e}",
                        exc_info=True,
                    )
                    self.console.print(
                        f"[red]Could not retrieve transcript for Job ID {self.job_id}. Aborting.[/red]"
                    )
                    return True  # Not a quota error

                # Reload metadata after initialization to ensure we have the latest state
                metadata = self._load_metadata_json(metadata_path)
                if not metadata:
                    # This case should ideally not happen if _initialize_metadata_json works, but serves as a safeguard
                    logger.critical(
                        f"Failed to load metadata from {metadata_path} after initialization. Aborting."
                    )
                    self.console.print(
                        f"[red]Failed to load metadata from {metadata_path} after initialization. Aborting.[/red]"
                    )
                    return True  # Not a quota error

                all_categories_successfully_processed = True  # Flag to track if all categories have been successfully generated
                # Iterate through each defined metadata category
                for category in config.METADATA_CATEGORIES:
                    # Check if the current category's value is missing or None
                    if metadata.get(category) is None:
                        logger.info(
                            f"Generating missing metadata: {category} for Job ID: {self.job_id}."
                        )
                        self.console.print(
                            f"[yellow]Generating missing metadata: {category}[/yellow]"
                        )

                        # Dynamically construct the method name for generating this category (e.g., '_generate_title')
                        generation_method_name = f"_generate_{category}"
                        # Get the actual method object using getattr
                        generation_method = getattr(self, generation_method_name, None)

                        if generation_method:
                            category_filled_this_attempt = (
                                False  # Flag for current category's success
                            )
                            # Display a status spinner in the console during LLM generation
                            status_message = (
                                f"Generating {category} for job {job.job_ulid}..."
                            )
                            with self.console.status(
                                status_message, spinner=config.SPINNER
                            ):
                                try:
                                    # Execute the generation method using the LLM client
                                    gemini_result = generation_method(
                                        transcript_text, metadata
                                    )
                                    if gemini_result.ok is True:
                                        # If LLM call was successful, update metadata and save to file
                                        metadata[category] = gemini_result.output
                                        self._save_metadata_json(
                                            metadata, metadata_path
                                        )
                                        self.console.print(
                                            f"[green]  {category} generated and saved.[/green]"
                                        )
                                        logger.info(
                                            f"Successfully generated and saved '{category}' for Job ID: {self.job_id}."
                                        )
                                        category_filled_this_attempt = True
                                    else:
                                        # Handle cases where the Gemini LLM call returns an error
                                        error_message = gemini_result.error_message
                                        # Check for a quota error specifically
                                        if "quota" in str(error_message).lower():
                                            logger.critical(
                                                f"Gemini API quota exceeded while generating '{category}' for Job ID {self.job_id}."
                                            )
                                            self.console.print(
                                                "[bold red]Gemini API quota exceeded. Stopping all metadata processing.[/bold red]"
                                            )
                                            logger.debug(
                                                f"Raw Gemini error output: {gemini_result.output}"
                                            )
                                            self.console.print(
                                                f"[red]  Gemini call for '{category}' failed. See logs for raw output and details.[/red]"
                                            )
                                            print(gemini_result.output)
                                            logging.shutdown()  # This flushes and closes all handlers
                                            return False  # Signal to stop everything

                                        logger.error(
                                            f"\n**********\nError with Gemini call for category '{category}'.\nError type: {gemini_result.error_type}\nError Message: {error_message}\nExit Code: {gemini_result.exit_code}\n*********\n"
                                        )
                                        logger.debug(
                                            f"Raw Gemini error output: {gemini_result.output}"
                                        )
                                        self.console.print(
                                            f"[red]  Gemini call for '{category}' failed. See logs for raw output and details.[/red]"
                                        )
                                        # Do not mark as all_categories_successfully_processed if this fails
                                except Exception:
                                    # Catch any unexpected errors during the generation process for a category
                                    logger.error(
                                        f"Error generating '{category}' for Job ID: {self.job_id}.",
                                        exc_info=True,
                                    )
                                    self.console.print(
                                        f"[red]  Error generating {category}. Check logs.[/red]"
                                    )
                                    logger.debug(
                                        f"Raw Gemini error output: {gemini_result.output}"
                                    )
                                    # Mark the category with an error placeholder and save, so it's not re-attempted immediately
                                    metadata[category] = (
                                        f"[ERROR] - See logs"  # Mark as error
                                    )
                                    self._save_metadata_json(
                                        metadata, metadata_path
                                    )  # Save error state
                                    # Do not mark as all_categories_successfully_processed if this fails

                            if not category_filled_this_attempt:
                                all_categories_successfully_processed = False
                                # If any category fails generation, we break from the loop for the current job
                                # to prevent further issues and allow the user to address the problem.
                                break  # Break if a category was not filled this attempt
                        else:
                            # This case indicates a developer error: a category is in config but no _generate_ method exists
                            logger.error(
                                f"Generation method for category '{category}' not found in MetadataExtractor. "
                                f"Please implement '_generate_{category}' or remove '{category}' from config.METADATA_CATEGORIES.",
                                exc_info=True,
                            )
                            self.console.print(
                                f"[red]  Error: Generation method for {category} not found. Check logs and configuration.[/red]"
                            )
                            all_categories_successfully_processed = (
                                False  # Cannot fill this category
                            )
                            break  # Break if a generation method is missing for a category

                # After attempting to fill all categories, update the database stage status
                if all_categories_successfully_processed:
                    # Find the 'extract_metadata' stage record for this job
                    metadata_stage = (
                        session.query(JobStage)
                        .filter_by(job_id=self.job_id, stage_name="extract_metadata")
                        .first()
                    )
                    # If the stage exists and is not already marked as successful, update it
                    if metadata_stage and metadata_stage.state != StageState.success:
                        metadata_stage.state = StageState.success
                        session.add(metadata_stage)
                        session.commit()  # Commit the change to the database
                        self.console.print(
                            f"[green]Job {job.job_ulid}: 'extract_metadata' stage marked as SUCCESS.[/green]"
                        )
                        logger.info(
                            f"Job ID {job.job_ulid}: 'extract_metadata' stage marked as SUCCESS in the database."
                        )
                    else:
                        logger.debug(
                            f"Job ID {job.job_ulid}: 'extract_metadata' stage was already successful or not found, no update needed."
                        )
                else:
                    logger.warning(
                        f"Job ID {job.job_ulid}: Not all metadata categories filled. "
                        f"'extract_metadata' stage remains pending/failed as some categories could not be generated."
                    )
                    self.console.print(
                        f"[yellow]Job {job.job_ulid}: Not all metadata categories filled. "
                        f"'extract_metadata' stage remains pending/failed.[/yellow]"
                    )
            return (
                True  # Processing for this job is done (or failed for non-quota reason)
            )
        except Exception:
            # Catch any critical unexpected errors that occur during the overall process_metadata execution
            logger.critical(
                f"A critical error occurred during metadata processing for Job ID: {self.job_id}.",
                exc_info=True,
            )
            self.console.print(
                f"[bold red]A critical error occurred during metadata processing for Job ID {self.job_id}. Check logs for details.[/bold red]"
            )
            return True  # Let the controller decide what to do next
