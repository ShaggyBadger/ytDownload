import logging
import json
import re
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from joshlib.ollama import OllamaClient
from config import config

logger = logging.getLogger(__name__)
console = Console()

class EvaluatorInitialization:
    """
    Handles the initialization of paragraphs.json files, ensuring they
    contain the necessary keys for the evaluation process.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def run_initialization(self, job_dir: Path):
        """
        Ensures that every paragraph in the job's paragraphs.json file
        has the required evaluation keys, adding them with default values
        if they are missing.

        Args:
            job_dir: The directory path for the specific job.
        """
        self.logger.info(f"Running evaluation initialization for job: {job_dir.name}")
        paragraphs_path = job_dir / config.PARAGRAPHS_FILE_NAME
        
        if not paragraphs_path.exists():
            self.logger.warning(f" paragraphs.json not found in {job_dir}. Skipping initialization.")
            return

        try:
            paragraphs = self._load_paragraphs(paragraphs_path)
            if paragraphs is None:
                return # Error logged in helper

            updated = False
            for para in paragraphs:
                # Set default values only if keys are missing
                if 'evaluation_status' not in para:
                    para['evaluation_status'] = 'pending'
                    updated = True
                if 'critique' not in para:
                    para['critique'] = None
                    updated = True
                if 'rating' not in para:
                    para['rating'] = None
                    updated = True
                if 'full_evaluation_output' not in para:
                    para['full_evaluation_output'] = None
                    updated = True

            if updated:
                self.logger.info("Evaluation keys were missing. Initializing and saving file.")
                self._save_paragraphs(paragraphs_path, paragraphs)
            else:
                self.logger.info("All evaluation keys already present. No initialization needed.")
                
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during initialization for {job_dir.name}: {e}", exc_info=True)

    def _load_paragraphs(self, file_path: Path) -> list | None:
        """Safely loads paragraphs from a JSON file."""
        try:
            with file_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Error reading or parsing {file_path}: {e}", exc_info=True)
            return None

    def _save_paragraphs(self, file_path: Path, data: list):
        """Safely saves paragraphs to a JSON file."""
        try:
            with file_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            self.logger.error(f"Error writing to {file_path}: {e}", exc_info=True)


class Evaluator:
    """
    Handles the evaluation of edited paragraphs in a paragraphs.json file.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ollama_client = OllamaClient(temperature=0.2)
        self.rating_threshold = 8

    def run_evaluation(self, job_dir: Path):
        """
        Runs the evaluation process for a specific job. It finds paragraphs
        that have not passed evaluation, evaluates them, and updates their
        status.

        Args:
            job_dir: The directory path for the specific job.
        """
        self.logger.info(f"Starting evaluation run for job: {job_dir.name}")
        paragraphs_path = job_dir / config.PARAGRAPHS_FILE_NAME
        
        if not paragraphs_path.exists():
            self.logger.error(f"Cannot run evaluation: {paragraphs_path} not found.")
            return

        paragraphs = self._load_paragraphs(paragraphs_path)
        if paragraphs is None:
            return

        indices_to_evaluate = [
            i for i, p in enumerate(paragraphs) if p.get('evaluation_status') != 'passed'
        ]

        if not indices_to_evaluate:
            self.logger.info(f"No paragraphs to evaluate for job {job_dir.name}.")
            return
            
        total_to_evaluate = len(indices_to_evaluate)
        self.logger.info(f"Found {total_to_evaluate} paragraphs to evaluate.")

        for count, index in enumerate(indices_to_evaluate, 1):
            with console.status(f"Evaluating paragraph {count}/{total_to_evaluate} for job {job_dir.name}...", spinner=config.SPINNER):
                try:
                    self._evaluate_paragraph(paragraphs, index, paragraphs_path)
                except Exception as e:
                    self.logger.critical(f"A critical error occurred while processing paragraph {index} in {job_dir.name}. Halting evaluation for this job. Error: {e}", exc_info=True)
                    break
    
    def _load_metadata(self, job_dir: Path) -> dict:
        """Loads metadata from metadata.json."""
        metadata_path = job_dir / config.METADATA_FILE_NAME
        if not metadata_path.exists():
            self.logger.warning(f"metadata.json not found in {job_dir}.")
            return {}
        try:
            with metadata_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Error reading or parsing {metadata_path}: {e}", exc_info=True)
            return {}

    def _evaluate_paragraph(self, all_paragraphs: list, index: int, paragraphs_path: Path):
        """
        Prepares, runs, and processes the evaluation for a single paragraph,
        and triggers regeneration if it fails.
        """
        self.logger.debug(f"Evaluating paragraph index {index}.")
        
        paragraph = all_paragraphs[index]
        job_dir = paragraphs_path.parent

        metadata = self._load_metadata(job_dir)
        thesis = metadata.get('thesis', '')
        tone = metadata.get('tone', '')

        # --- Build the evaluation prompt ---
        evaluation_prompt = self._build_evaluation_prompt(all_paragraphs, index, thesis, tone)
        self.logger.debug(f"Submitting prompt:\n{evaluation_prompt}")

        # --- Submit to Ollama and process response ---
        try:
            response_text = self.ollama_client.submit_prompt(evaluation_prompt)
            paragraph['full_evaluation_output'] = response_text
            evaluation_data = self._parse_evaluation_response(response_text)

            if evaluation_data:
                self._update_paragraph_status(paragraph, evaluation_data)
            else:
                self.logger.warning(f"Could not parse evaluation response for paragraph {index}. Status set to 'failed'.")
                paragraph['evaluation_status'] = 'failed'
                paragraph['critique'] = "Failed to parse model output."
                paragraph['rating'] = None

        except Exception as e:
            self.logger.error(f"Ollama processing failed for paragraph {index}: {e}", exc_info=True)
            paragraph['evaluation_status'] = 'failed'
            paragraph['critique'] = "Ollama processing error."
            paragraph['rating'] = None

        # --- Trigger regeneration if evaluation failed ---
        if paragraph.get('evaluation_status') == 'failed' and paragraph.get('critique'):
            self.logger.info(f"Paragraph {index} failed evaluation with rating {paragraph.get('rating')}. Regenerating.")
            self._regenerate_edited_paragraph(paragraph, all_paragraphs, index, tone)
        
        # --- Save changes ---
        self._save_paragraphs(paragraphs_path, all_paragraphs)
        self.logger.debug(f"Successfully processed paragraph {index}. New status: {paragraph['evaluation_status']}")

    def _build_evaluation_prompt(self, all_paragraphs: list, index: int, thesis: str, tone: str) -> str:
        """Builds the complete evaluation prompt string."""
        paragraph = all_paragraphs[index]
        total_paragraphs = len(all_paragraphs)
        
        previous_edited_text = all_paragraphs[index - 1].get('edited', '') if index > 0 else "This is the first paragraph."
        next_edited_text = all_paragraphs[index + 1].get('edited', '') if index < total_paragraphs - 1 else "This is the last paragraph."
        critique_for_redo = paragraph.get('critique') or ""

        prompt_name = self._get_prompt_name(index, total_paragraphs)
        prompts_dir = Path(__file__).resolve().parent / "prompts/evaluation"
        prompt_template_path = prompts_dir / prompt_name
        
        if not prompt_template_path.exists():
            self.logger.error(f"Evaluation prompt template not found: {prompt_template_path}")
            return "[EVALUATION PROMPT TEMPLATE NOT FOUND]"

        prompt_template = prompt_template_path.read_text()
        prompt_data = {
            'OG': paragraph.get('original', ''),
            'EP': paragraph.get('edited', ''),
            'PREV': previous_edited_text,
            'NEXT': next_edited_text,
            'THESIS': thesis,
            'TONE': tone,
            'CRITIQUE': critique_for_redo
        }
        return prompt_template.format(**prompt_data)

    def _regenerate_edited_paragraph(self, paragraph: dict, all_paragraphs: list, index: int, tone: str):
        """Builds a new prompt to regenerate a failed paragraph and updates it."""
        self.logger.info(f"Building regeneration prompt for paragraph {index}.")
        total_paragraphs = len(all_paragraphs)
        
        # --- Build the base editor prompt using original context ---
        editor_prompt_name = self._get_prompt_name(index, total_paragraphs)
        editor_prompts_dir = Path(__file__).resolve().parent / "prompts/editor"
        editor_template_path = editor_prompts_dir / editor_prompt_name

        if not editor_template_path.exists():
            self.logger.error(f"Editor prompt template not found: {editor_template_path}")
            paragraph['critique'] += "\n[REGENERATION FAILED: Editor prompt template not found.]"
            return

        # Use original surrounding paragraphs for context, consistent with first-pass editing
        prev_original_text = all_paragraphs[index - 1].get('original', '') if index > 0 else "This is the first paragraph."
        next_original_text = all_paragraphs[index + 1].get('original', '') if index < total_paragraphs - 1 else "This is the last paragraph."

        editor_template = editor_template_path.read_text()
        editor_prompt_data = {
            'SPEAKER_TONE': tone,
            'PARAGRAPH_PREV': prev_original_text,
            'PARAGRAPH_TARGET': paragraph.get('original', ''),
            'PARAGRAPH_NEXT': next_original_text
        }
        filled_editor_prompt = editor_template.format(**editor_prompt_data)

        # --- Build the revision addendum prompt ---
        addendum_path = editor_prompts_dir / "revision-addendum.txt"
        if not addendum_path.exists():
            self.logger.error(f"Revision addendum prompt not found: {addendum_path}")
            paragraph['critique'] += "\n[REGENERATION FAILED: Revision addendum prompt not found.]"
            return
            
        addendum_template = addendum_path.read_text()
        critique = paragraph.get('critique', 'No critique provided.')
        filled_addendum = addendum_template.format(CRITIQUE=critique)

        # --- Combine and submit ---
        final_prompt = filled_editor_prompt + "\n" + filled_addendum
        self.logger.debug(f"Submitting regeneration prompt:\n{final_prompt}")
        
        try:
            new_edited_text = self.ollama_client.submit_prompt(final_prompt)
            paragraph['edited'] = new_edited_text
            paragraph['evaluation_status'] = 'regenerated'
            self.logger.info(f"Paragraph {index} successfully regenerated.")
        except Exception as e:
            self.logger.error(f"Ollama processing failed during regeneration for paragraph {index}: {e}", exc_info=True)
            paragraph['critique'] += "\n[REGENERATION FAILED: Ollama client error.]"
            return

    def _get_prompt_name(self, index: int, total: int) -> str:
        """Determines which prompt file to use."""
        if index == 0:
            return "evaluate-paragraph-first.txt"
        elif index == total - 1:
            return "evaluate-paragraph-last.txt"
        else:
            return "evaluate-paragraph-standard.txt"

    def _parse_evaluation_response(self, response_text: str) -> dict | None:
        """Parses the text response from the Ollama model."""
        try:
            # Extract Rating
            rating_match = re.search(r"Rating: (\d+)", response_text)
            if not rating_match:
                self.logger.error(f"Could not find 'Rating:' in model response.")
                self.logger.debug(f"Problematic response text:\n{response_text}")
                return None
            rating = int(rating_match.group(1))

            # Extract Critique
            critique_match = re.search(r"CRITIQUE FOR REDO:\n<<<\n(.*?)\n>>>", response_text, re.DOTALL)
            if not critique_match:
                self.logger.error(f"Could not find 'CRITIQUE FOR REDO:' block in model response.")
                self.logger.debug(f"Problematic response text:\n{response_text}")
                return None
            
            critique = critique_match.group(1).strip()
            if critique.lower() == 'none':
                critique = None

            return {"rating": rating, "critique": critique}
            
        except Exception as e:
            self.logger.error(f"An error occurred while parsing evaluation response: {e}", exc_info=True)
            self.logger.debug(f"Problematic response text:\n{response_text}")
            return None

    def _update_paragraph_status(self, paragraph: dict, eval_data: dict):
        """Updates the paragraph object with evaluation results."""
        rating = eval_data.get('rating')
        critique = eval_data.get('critique')

        paragraph['critique'] = critique
        paragraph['rating'] = rating

        if rating is not None and isinstance(rating, int):
            if rating >= self.rating_threshold:
                paragraph['evaluation_status'] = 'passed'
            else:
                paragraph['evaluation_status'] = 'failed'
        else:
            self.logger.warning(f"Rating is missing or not an integer: {rating}. Defaulting to 'failed'.")
            paragraph['evaluation_status'] = 'failed'

    def _load_paragraphs(self, file_path: Path) -> list | None:
        """Safely loads paragraphs from a JSON file."""
        try:
            with file_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Error reading or parsing {file_path}: {e}", exc_info=True)
            return None

    def _save_paragraphs(self, file_path: Path, data: list):
        """Safely saves paragraphs to a JSON file."""
        try:
            with file_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            self.logger.error(f"Error writing to {file_path}: {e}", exc_info=True)