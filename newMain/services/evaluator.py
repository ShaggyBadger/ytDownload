import logging
import json
import re
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

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
            self.logger.warning(
                f" paragraphs.json not found in {job_dir}. Skipping initialization."
            )
            return

        try:
            paragraphs = self._load_paragraphs(paragraphs_path)
            if paragraphs is None:
                return  # Error logged in helper

            updated = False
            for para in paragraphs:
                # Set default values only if keys are missing
                if "evaluation_status" not in para:
                    para["evaluation_status"] = "pending"
                    updated = True
                if "critique" not in para:
                    para["critique"] = None
                    updated = True
                if "rating" not in para:
                    para["rating"] = None
                    updated = True
                if "full_evaluation_output" not in para:
                    para["full_evaluation_output"] = None
                    updated = True
                if "regeneration_prompt" not in para:
                    para["regeneration_prompt"] = None
                    updated = True

            if updated:
                self.logger.info(
                    "Evaluation keys were missing. Initializing and saving file."
                )
                self._save_paragraphs(paragraphs_path, paragraphs)
            else:
                self.logger.info(
                    "All evaluation keys already present. No initialization needed."
                )

        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred during initialization for {job_dir.name}: {e}",
                exc_info=True,
            )

    def _load_paragraphs(self, file_path: Path) -> list | None:
        """Safely loads paragraphs from a JSON file."""
        try:
            with file_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(
                f"Error reading or parsing {file_path}: {e}", exc_info=True
            )
            return None

    def _save_paragraphs(self, file_path: Path, data: list):
        """Safely saves paragraphs to a JSON file."""
        try:
            with file_path.open("w", encoding="utf-8") as f:
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
            i
            for i, p in enumerate(paragraphs)
            if p.get("evaluation_status") != "passed"
        ]

        if not indices_to_evaluate:
            self.logger.info(f"No paragraphs to evaluate for job {job_dir.name}.")
            return

        total_to_evaluate = len(indices_to_evaluate)
        self.logger.info(f"Found {total_to_evaluate} paragraphs to evaluate.")

        for count, index in enumerate(indices_to_evaluate, 1):
            with console.status(
                f"Evaluating paragraph {count}/{total_to_evaluate} for job {job_dir.name}...",
                spinner=config.SPINNER,
            ):
                try:
                    self._evaluate_paragraph(paragraphs, index, paragraphs_path)
                except Exception as e:
                    self.logger.critical(
                        f"A critical error occurred while processing paragraph {index} in {job_dir.name}. Halting evaluation for this job. Error: {e}",
                        exc_info=True,
                    )
                    break

    def _load_metadata(self, job_dir: Path) -> dict:
        """Loads metadata from metadata.json."""
        metadata_path = job_dir / config.METADATA_FILE_NAME
        if not metadata_path.exists():
            self.logger.warning(f"metadata.json not found in {job_dir}.")
            return {}
        try:
            with metadata_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(
                f"Error reading or parsing {metadata_path}: {e}", exc_info=True
            )
            return {}

    def _evaluate_paragraph(
        self, all_paragraphs: list, index: int, paragraphs_path: Path
    ):
        """
        Prepares, runs, and processes the evaluation for a single paragraph,
        and triggers regeneration if it fails.
        """
        self.logger.debug(f"Evaluating paragraph index {index}.")

        paragraph = all_paragraphs[index]
        job_dir = paragraphs_path.parent

        metadata = self._load_metadata(job_dir)
        thesis = metadata.get("thesis", "")
        tone = metadata.get("tone", "")

        # --- Build the evaluation prompt ---
        evaluation_prompt = self._build_evaluation_prompt(
            all_paragraphs, index, thesis, tone
        )
        self.logger.debug(f"Submitting prompt...")

        # --- Submit to Ollama and process response ---
        try:
            response_text = self.ollama_client.submit_prompt(evaluation_prompt)
            paragraph["full_evaluation_output"] = response_text
            evaluation_data = self._parse_evaluation_response(response_text)

            if evaluation_data:
                self._update_paragraph_status(paragraph, evaluation_data)
            else:
                self.logger.warning(
                    f"Could not parse evaluation response for paragraph {index}. Status set to 'failed'."
                )
                paragraph["evaluation_status"] = "failed"
                paragraph["critique"] = "Failed to parse model output."
                paragraph["rating"] = None

        except Exception as e:
            self.logger.error(
                f"Ollama processing failed for paragraph {index}: {e}", exc_info=True
            )
            paragraph["evaluation_status"] = "failed"
            paragraph["critique"] = "Ollama processing error."
            paragraph["rating"] = None

        # --- Trigger regeneration if evaluation failed ---
        if paragraph.get("evaluation_status") == "failed" and paragraph.get("critique"):
            self.logger.info(
                f"Paragraph {index} failed evaluation with rating {paragraph.get('rating')}. Regenerating."
            )
            self._regenerate_edited_paragraph(paragraph, all_paragraphs, index, tone)

        # --- Save changes ---
        self._save_paragraphs(paragraphs_path, all_paragraphs)
        self.logger.debug(
            f"Successfully processed paragraph {index}. New status: {paragraph['evaluation_status']}"
        )

    def _build_evaluation_prompt(
        self, all_paragraphs: list, index: int, thesis: str, tone: str
    ) -> str:
        """Builds the complete evaluation prompt string."""
        paragraph = all_paragraphs[index]
        total_paragraphs = len(all_paragraphs)

        previous_edited_text = (
            all_paragraphs[index - 1].get("edited", "")
            if index > 0
            else "This is the first paragraph."
        )
        next_edited_text = (
            all_paragraphs[index + 1].get("edited", "")
            if index < total_paragraphs - 1
            else "This is the last paragraph."
        )
        critique_for_redo = paragraph.get("critique") or ""

        prompt_name = self._get_prompt_name(index, total_paragraphs)
        prompts_dir = Path(__file__).resolve().parent / "prompts/evaluation"
        prompt_template_path = prompts_dir / prompt_name

        if not prompt_template_path.exists():
            self.logger.error(
                f"Evaluation prompt template not found: {prompt_template_path}"
            )
            return "[EVALUATION PROMPT TEMPLATE NOT FOUND]"

        prompt_template = prompt_template_path.read_text()
        prompt_data = {
            "OG": paragraph.get("original", ""),
            "EP": paragraph.get("edited", ""),
            "PREV": previous_edited_text,
            "NEXT": next_edited_text,
            "THESIS": thesis,
            "TONE": tone,
            "CRITIQUE": critique_for_redo,
        }
        return prompt_template.format(**prompt_data)

    def _regenerate_edited_paragraph(
        self, paragraph: dict, all_paragraphs: list, index: int, tone: str
    ):
        """Builds a new prompt to regenerate a failed paragraph and updates it."""
        self.logger.info(f"Building regeneration prompt for paragraph {index}.")

        # --- Get the original editor prompt from the paragraph data ---
        # This prompt was saved during the initial editing pass.
        original_editor_prompt = paragraph.get("prompt")
        if not original_editor_prompt:
            self.logger.error(
                f"Cannot regenerate paragraph {index}: Original 'prompt' is missing from paragraph data."
            )
            return

        # --- Build the revision addendum prompt ---
        editor_prompts_dir = Path(__file__).resolve().parent / "prompts/evaluation"
        addendum_path = editor_prompts_dir / "revision-addendum.txt"
        if not addendum_path.exists():
            self.logger.error(f"Revision addendum prompt not found: {addendum_path}")
            return

        addendum_template = addendum_path.read_text()
        critique = paragraph.get("critique", "No critique provided.")
        filled_addendum = addendum_template.format(CRITIQUE=critique)

        # --- Combine and submit ---
        final_prompt = original_editor_prompt + "\n\n" + filled_addendum

        try:
            self.logger.debug("Submitting re-edit prompt to LLM...")
            new_edited_text = self.ollama_client.submit_prompt(final_prompt)
            self.logger.debug("LLM edit complete.")
            paragraph["edited"] = new_edited_text
            paragraph["evaluation_status"] = "regenerated"
            # Also store the prompt that led to this regeneration
            paragraph["regeneration_prompt"] = final_prompt

            # update the status for this paragraph
            paragraph["evaluation_status"] = "regenerated"
            self.logger.info(f"Paragraph {index} successfully regenerated.")
        except Exception as e:
            self.logger.error(
                f"Ollama processing failed during regeneration for paragraph {index}: {e}",
                exc_info=True,
            )
            paragraph["critique"] += "\n[REGENERATION FAILED: Ollama client error.]"
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
            critique_match = re.search(
                r"CRITIQUE FOR REDO:\n(.*?)(?=\n\n|\Z)", response_text, re.DOTALL
            )
            if not critique_match:
                self.logger.error(
                    f"Could not find 'CRITIQUE FOR REDO:' block in model response."
                )
                self.logger.debug(f"Problematic response text:\n{response_text}")
                return None

            critique = critique_match.group(1).strip()
            if critique.lower() == "none":
                critique = None

            return {"rating": rating, "critique": critique}

        except Exception as e:
            self.logger.error(
                f"An error occurred while parsing evaluation response: {e}",
                exc_info=True,
            )
            self.logger.debug(f"Problematic response text:\n{response_text}")
            return None

    def _update_paragraph_status(self, paragraph: dict, eval_data: dict):
        """Updates the paragraph object with evaluation results."""
        rating = eval_data.get("rating")
        critique = eval_data.get("critique")

        paragraph["critique"] = critique
        paragraph["rating"] = rating

        if rating is not None and isinstance(rating, int):
            if rating >= self.rating_threshold:
                paragraph["evaluation_status"] = "passed"
            else:
                paragraph["evaluation_status"] = "failed"
        else:
            self.logger.warning(
                f"Rating is missing or not an integer: {rating}. Defaulting to 'failed'."
            )
            paragraph["evaluation_status"] = "failed"

    def _load_paragraphs(self, file_path: Path) -> list | None:
        """Safely loads paragraphs from a JSON file."""
        try:
            with file_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(
                f"Error reading or parsing {file_path}: {e}", exc_info=True
            )
            return None

    def _save_paragraphs(self, file_path: Path, data: list):
        """Safely saves paragraphs to a JSON file."""
        try:
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            self.logger.error(f"Error writing to {file_path}: {e}", exc_info=True)


class UserInteractiveEvaluator:
    """
    Allows the user to interactively evaluate the quality of a regenerated paragraph.
    """

    def __init__(self, console: Console):
        self.logger = logging.getLogger(__name__)
        self.console = console
        self.evaluator_service = Evaluator()  # Instantiate the Evaluator service

    def evaluate_single_job(self):
        """
        Guides the user to select a single job and evaluates its eligible paragraphs
        interactively.
        """
        eligible_jobs = self._get_eligible_jobs_for_user_evaluation()
        if not eligible_jobs:
            self.console.print(
                "[yellow]No jobs found with regenerated paragraphs needing user evaluation.[/yellow]"
            )
            return

        self.console.print("\n[bold cyan]Select a job to evaluate:[/bold cyan]")
        for i, job_dir in enumerate(eligible_jobs):
            self.console.print(f"{i + 1}. {job_dir.name}")

        while True:
            choice = Prompt.ask(
                "Enter job number (or 'q' to quit)",
                choices=[str(i + 1) for i in range(len(eligible_jobs))] + ["q"],
            ).lower()
            if choice == "q":
                return
            try:
                selected_index = int(choice) - 1
                if 0 <= selected_index < len(eligible_jobs):
                    selected_job_dir = eligible_jobs[selected_index]
                    self._evaluate_job_interactively(selected_job_dir)
                    break
                else:
                    self.console.print("[red]Invalid job number.[/red]")
            except ValueError:
                self.console.print(
                    "[red]Invalid input. Please enter a number or 'q'.[/red]"
                )

    def evaluate_all_jobs(self):
        """
        Evaluates all eligible jobs interactively, processing paragraphs that are
        marked as 'regenerated' and awaiting user review.
        """
        eligible_jobs = self._get_eligible_jobs_for_user_evaluation()
        if not eligible_jobs:
            self.console.print(
                "[yellow]No jobs found with regenerated paragraphs needing user evaluation.[/yellow]"
            )
            return

        self.console.print(
            f"\n[bold green]Starting interactive evaluation for {len(eligible_jobs)} job(s).[/bold green]"
        )
        for job_dir in eligible_jobs:
            self._evaluate_job_interactively(job_dir)

        self.console.print(
            "\n[bold green]Interactive evaluation complete for all eligible jobs.[/bold green]"
        )

    def _evaluate_job_interactively(self, job_dir: Path):
        """
        Evaluates a single job by iterating through its 'regenerated' paragraphs
        and prompting the user for input.
        """
        self.logger.info(f"Starting interactive evaluation for job: {job_dir.name}")
        paragraphs_path = job_dir / config.PARAGRAPHS_FILE_NAME

        if not paragraphs_path.exists():
            self.console.print(
                f"[red]Error: paragraphs.json not found in {job_dir}. Skipping.[/red]"
            )
            self.logger.error(
                f"paragraphs.json not found in {job_dir}. Skipping interactive evaluation."
            )
            return

        paragraphs = self._load_paragraphs(paragraphs_path)
        if paragraphs is None:
            self.console.print(
                f"[red]Error loading paragraphs from {paragraphs_path}. Skipping.[/red]"
            )
            return

        # Initialize EvaluatorInitialization for a job if not already done.
        # This ensures all paragraphs have necessary keys for evaluation.
        EvaluatorInitialization().run_initialization(job_dir)

        paragraphs_to_evaluate_indices = [
            i
            for i, p in enumerate(paragraphs)
            if p.get("evaluation_status") == "regenerated"
        ]

        if not paragraphs_to_evaluate_indices:
            self.console.print(
                f"[yellow]No regenerated paragraphs needing user evaluation in job: {job_dir.name}.[/yellow]"
            )
            self.logger.info(
                f"No regenerated paragraphs needing user evaluation in job: {job_dir.name}."
            )
            return

        self.console.print(
            f"\n[bold blue]--- Evaluating Job: {job_dir.name} ---[/bold blue]"
        )
        for index in paragraphs_to_evaluate_indices:
            paragraph_data = paragraphs[index]

            # This is the new orchestration
            user_decision = self._run_llm_evaluation_and_display(
                paragraph_data, index, job_dir, paragraphs
            )

            self._update_paragraph_status_from_user_input(paragraph_data, user_decision)
            self._save_paragraphs(
                paragraphs_path, paragraphs
            )  # Save after each paragraph

        self.console.print(
            f"[bold green]Interactive evaluation complete for job: {job_dir.name}.[/bold green]"
        )
        self.logger.info(f"Interactive evaluation complete for job: {job_dir.name}.")

    def _get_eligible_jobs_for_user_evaluation(self) -> list[Path]:
        """
        Fetches job directories that contain paragraphs with an 'evaluation_status' of 'regenerated'.
        """
        self.logger.debug("Gathering eligible job directories for user evaluation.")
        main_dir = config.PROJECT_ROOT / "jobs"
        all_job_dirs = [p for p in main_dir.iterdir() if p.is_dir()]
        eligible_jobs = []

        for job_dir in all_job_dirs:
            paragraphs_path = job_dir / config.PARAGRAPHS_FILE_NAME
            if paragraphs_path.exists():
                paragraphs = self._load_paragraphs(paragraphs_path)
                if paragraphs and any(
                    p.get("evaluation_status") == "regenerated" for p in paragraphs
                ):
                    eligible_jobs.append(job_dir)
            else:
                self.logger.warning(
                    f"paragraphs.json not found for job: {job_dir.name}"
                )

        eligible_jobs.sort(key=lambda p: p.name)
        self.logger.debug(
            f"Found {len(eligible_jobs)} eligible jobs for user evaluation."
        )
        return eligible_jobs

    def _run_llm_evaluation_and_display(
        self, paragraph_data: dict, index: int, job_dir: Path, all_paragraphs: list
    ):
        """
        Displays original/edited text, current critique/rating, runs LLM evaluation with a spinner,
        displays new results, and prompts user for decision.
        """
        original = paragraph_data.get("original", "[N/A]")
        edited = paragraph_data.get("edited", "[N/A]")

        # New: Display current rating and critique
        current_critique = paragraph_data.get(
            "critique", "[No previous critique available.]"
        )
        current_rating = paragraph_data.get("rating", "N/A")

        self.console.print(f"\n[bold magenta]Paragraph {index + 1}[/bold magenta]")
        self.console.print(
            Panel(
                f"[bold yellow]Original:[/bold yellow]\n{original}\n\n"
                f"[bold green]Edited:[/bold green]\n{edited}\n\n"
                f"[bold purple]Previous Critique:[/bold purple] {current_critique}\n"
                f"[bold blue]Previous Rating:[/bold blue] {current_rating}/10",
                title=f"[bold yellow]Paragraph {index + 1} - Review (Before Re-evaluation)[/bold yellow]",
                border_style="cyan",
            )
        )

        # 2. Run LLM with spinner
        metadata = self.evaluator_service._load_metadata(job_dir)
        thesis = metadata.get("thesis", "")
        tone = metadata.get("tone", "")

        evaluation_prompt = self.evaluator_service._build_evaluation_prompt(
            all_paragraphs, index, thesis, tone
        )

        new_rating = "N/A"
        new_critique = "[LLM did not provide a critique.]"
        llm_full_output = ""

        with self.console.status(
            "[bold blue]Running LLM evaluation...[/bold blue]", spinner=config.SPINNER
        ):
            try:
                llm_full_output = self.evaluator_service.ollama_client.submit_prompt(
                    evaluation_prompt
                )
                evaluation_data = self.evaluator_service._parse_evaluation_response(
                    llm_full_output
                )

                if evaluation_data:
                    new_rating = evaluation_data.get("rating", "N/A")
                    new_critique = evaluation_data.get(
                        "critique", "[LLM did not provide a critique.]"
                    )
                else:
                    self.logger.warning(
                        f"Could not parse LLM evaluation response for paragraph {index}."
                    )

            except Exception as e:
                self.logger.error(
                    f"Error during LLM evaluation for paragraph {index}: {e}",
                    exc_info=True,
                )
                new_critique = f"[ERROR during LLM evaluation: {e}]"

        # 3. Display new results
        self.console.print(
            Panel(
                f"[bold red]New Critique:[/bold red] {new_critique}\n"
                f"[bold blue]New Rating:[/bold blue] {new_rating}/10",
                title="[bold yellow]LLM Evaluation Results[/bold yellow]",
                border_style="magenta",
            )
        )

        # Update paragraph_data with new evaluation results
        paragraph_data["rating"] = new_rating
        paragraph_data["critique"] = new_critique
        paragraph_data["full_evaluation_output"] = llm_full_output

        # 4. Prompt for user decision in a loop
        while True:
            user_decision = self._get_user_evaluation()
            if user_decision == "v":
                self.console.print(
                    Panel(
                        llm_full_output,
                        title="[bold blue]Full LLM Response[/bold blue]",
                        border_style="blue",
                    )
                )
                self.console.input("Press Enter to continue...")
                # The loop continues, re-offering the accept/reject menu
            else:
                return user_decision  # Return y, n, or s

    def _get_user_evaluation(self) -> str:
        """
        Prompts the user for their evaluation (pass/fail/skip/view full response).
        """
        return Prompt.ask(
            "Keep this edit? ([bold green]y[/bold green]/[bold red]n[/bold red]/[bold yellow]s[/bold yellow]kip/[bold blue]v[/bold blue]iew full LLM response)",
            choices=["y", "n", "s", "v"],
            default="y",
        ).lower()

    def _update_paragraph_status_from_user_input(
        self, paragraph_data: dict, user_decision: str
    ):
        """
        Updates the evaluation status of the paragraph based on user input.
        """
        if user_decision == "y":
            paragraph_data["evaluation_status"] = "passed"
            self.logger.info("User accepted the regenerated paragraph.")
        elif user_decision == "n":
            paragraph_data["evaluation_status"] = (
                "failed"  # User rejected, so it needs another regeneration cycle
            )
            self.logger.info("User rejected the regenerated paragraph.")
        elif user_decision == "s":
            paragraph_data["evaluation_status"] = (
                "regenerated"  # Keep as regenerated for later
            )
            self.logger.info("User skipped evaluation for this paragraph.")
        else:
            self.logger.warning(
                f"Unknown user decision: {user_decision}. Status not changed."
            )

    def _load_paragraphs(self, file_path: Path) -> list | None:
        """Safely loads paragraphs from a JSON file."""
        try:
            with file_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(
                f"Error reading or parsing {file_path}: {e}", exc_info=True
            )
            return None

    def _save_paragraphs(self, file_path: Path, data: list):
        """Safely saves paragraphs to a JSON file."""
        try:
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            self.logger.error(f"Error writing to {file_path}: {e}", exc_info=True)


if __name__ == "__main__":
    evaluator = RegeneratedEvaluation()
    evaluator.run()
