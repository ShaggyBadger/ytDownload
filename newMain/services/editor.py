from pathlib import Path
import json
import re # Added re import

from joshlib.ollama import OllamaClient
from rich.console import Console

from database.session_manager import get_session
from database.models import JobInfo, JobStage, StageState # Added StageState
from config import config

class Editor:
    """Class to handle paragraph editing using Ollama API."""

    def __init__(self, job_id):
        """A class to handle paragraph-by-paragraph editing of a sermon."""
        self.job_id = job_id
        self.console = Console()
        self.ollama_client = OllamaClient(temperature=0.65)

    def _build_paragraphs_json_data(self, transcript_text, job_directory):
        """Builds the initial data structure for paragraphs.json."""
        # Initialize paths for prompts directory
        BASE_DIR = Path(__file__).resolve().parent
        PROMPTS_DIR = BASE_DIR / "prompts/editor"

        # Read speaker tone from metadata.json
        speaker_tone = "neutral"  # Default tone
        metadata_path = Path(job_directory) / config.METADATA_FILE_NAME
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    speaker_tone = metadata.get('tone', 'neutral')
            except Exception as e:
                self.console.print(f"[red]Error reading metadata.json for tone: {e}[/red]")
        self.console.print(f"[dim]Speaker tone for prompts: {speaker_tone}[/dim]")

        # load prompt templates
        standard_prompt_path = PROMPTS_DIR / "edit-paragraph-standard.txt"
        first_paragraph_prompt_path = PROMPTS_DIR / "edit-paragraph-first.txt"
        last_paragraph_prompt_path = PROMPTS_DIR / "edit-paragraph-last.txt"

        # Use regex to split by one or more newlines
        paragraphs = [p.strip() for p in re.split(r'\n+', transcript_text) if p.strip()]
        paragraphs_data = []
        total_paragraphs = len(paragraphs)

        for i, paragraph in enumerate(paragraphs):
            prompt = ""
            try:
                if i == 0 and total_paragraphs > 1:
                    prompt_template = first_paragraph_prompt_path.read_text()
                    prompt = prompt_template.format(SPEAKER_TONE=speaker_tone, PARAGRAPH_TARGET=paragraph, PARAGRAPH_NEXT=paragraphs[i + 1])
                elif i == total_paragraphs - 1 and total_paragraphs > 1:
                    prompt_template = last_paragraph_prompt_path.read_text()
                    prompt = prompt_template.format(SPEAKER_TONE=speaker_tone, PARAGRAPH_TARGET=paragraph, PARAGRAPH_PREV=paragraphs[i - 1])
                elif total_paragraphs > 1:
                    prompt_template = standard_prompt_path.read_text()
                    prompt = prompt_template.format(SPEAKER_TONE=speaker_tone, PARAGRAPH_TARGET=paragraph, PARAGRAPH_PREV=paragraphs[i - 1], PARAGRAPH_NEXT=paragraphs[i + 1])
                else: # Handle case with only one paragraph
                    prompt_template = first_paragraph_prompt_path.read_text() # Or a specific single-paragraph prompt
                    prompt = prompt_template.format(SPEAKER_TONE=speaker_tone, PARAGRAPH_TARGET=paragraph, PARAGRAPH_NEXT="")

                paragraph_entry = {
                    'index': i,
                    'original': paragraph,
                    'prompt': prompt,
                    'edited': None
                }
                paragraphs_data.append(paragraph_entry)

            except FileNotFoundError as e:
                self.console.print(f"[red]Error: Prompt file not found - {e}[/red]")
                paragraphs_data.append({'index': i, 'original': paragraph, 'prompt': '[PROMPT FILE NOT FOUND]', 'edited': None})
            except Exception as e:
                self.console.print(f"[red]Error creating prompt for paragraph {i}: {e}[/red]")
                paragraphs_data.append({'index': i, 'original': paragraph, 'prompt': '[ERROR CREATING PROMPT]', 'edited': None})

        return paragraphs_data

    def _save_paragraphs_to_file(self, data, file_path):
        """Saves the paragraph data to the JSON file."""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            # self.console.print(f"[green]Successfully saved paragraph data to {file_path}[/green]") # Commented out for less verbosity during bulk processing
        except Exception as e:
            self.console.print(f"[red]Error saving paragraph data: {e}[/red]")

    def _load_paragraphs_from_file(self, file_path):
        """Loads paragraph data from a JSON file."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.console.print(f"[red]Error: Paragraphs JSON file not found at {file_path}[/red]")
            return None
        except json.JSONDecodeError as e:
            self.console.print(f"[red]Error decoding JSON from {file_path}: {e}[/red]")
            return None
        except Exception as e:
            self.console.print(f"[red]Error loading paragraphs from {file_path}: {e}[/red]")
            return None

    def _get_paragraph_file_path(self, job_directory):
        """Returns the path for the paragraphs.json file for a given sermon."""
        return Path(job_directory) / config.PARAGRAPHS_FILE_NAME

    def run_editor(self):
        """Orchestrates the sermon editing process (initial JSON creation)."""
        with get_session() as session:
            job = session.query(JobInfo).filter(JobInfo.id == self.job_id).first()
            if not job:
                self.console.print(f"[red]Job with ID {self.job_id} not found.[/red]")
                return

            self.console.print(f"Processing job: {job.job_ulid}")

            # Find the 'format_gemini' stage
            format_gemini_stage = session.query(JobStage).filter(
                JobStage.job_id == self.job_id,
                JobStage.stage_name == "format_gemini"
            ).first()

            if not format_gemini_stage or not format_gemini_stage.output_path:
                self.console.print("[red]Formatted transcript path not found for this job.[/red]")
                return

            transcript_path = Path(format_gemini_stage.output_path)
            if not transcript_path.exists():
                self.console.print(f"[red]Transcript file not found at {transcript_path}[/red]")
                return

            paragraph_file_path = self._get_paragraph_file_path(job.job_directory)

            if paragraph_file_path.exists():
                self.console.print(f"[yellow]Paragraphs JSON file already exists at {paragraph_file_path}. Skipping creation.[/yellow]")
            else:
                self.console.print("Paragraphs JSON file not found. Creating...")
                transcript_text = transcript_path.read_text()
                paragraphs_data = self._build_paragraphs_json_data(transcript_text, job.job_directory)
                self._save_paragraphs_to_file(paragraphs_data, paragraph_file_path)
                
                # Update the database
                format_gemini_stage.paragraph_json_path = str(paragraph_file_path)
                session.commit()
                self.console.print(f"Updated database with path: {paragraph_file_path}")

    def process_paragraphs_for_editing(self):
        """
        Loads the paragraphs.json, sends unedited paragraphs to Ollama for processing,
        and saves results intermittently.
        """
        with get_session() as session:
            job = session.query(JobInfo).filter(JobInfo.id == self.job_id).first()
            if not job:
                self.console.print(f"[red]Job with ID {self.job_id} not found.[/red]")
                return

            self.console.print(f"Starting paragraph editing for job: {job.job_ulid}")

            # Get the path to the paragraphs.json file
            paragraph_file_path = self._get_paragraph_file_path(job.job_directory)
            if not paragraph_file_path.exists():
                self.console.print(f"[red]Paragraphs JSON file not found for job {job.job_ulid} at {paragraph_file_path}. Skipping editing.[/red]")
                return

            paragraphs_data = self._load_paragraphs_from_file(paragraph_file_path)
            if paragraphs_data is None:
                return # Error already reported by _load_paragraphs_from_file

            total_paragraphs = len(paragraphs_data)
            edited_count = 0

            for i, paragraph_entry in enumerate(paragraphs_data):
                if paragraph_entry.get('edited') is None:
                    status_message = f"Processing paragraph {i+1}/{total_paragraphs} for job {job.job_ulid}..."
                    with self.console.status(status_message, spinner=config.SPINNER):
                        try:
                            # Send prompt to Ollama client
                            ollama_response = self.ollama_client.submit_prompt(paragraph_entry['prompt'])
                            paragraph_entry['edited'] = ollama_response
                            edited_count += 1
                            # The console.status automatically clears, so no separate print for success needed here immediately
                            # self.console.print(f"[green]  Paragraph {i+1} edited successfully.[/green]") # Removed for cleaner output

                            # Save after each edit to ensure progress is saved
                            self._save_paragraphs_to_file(paragraphs_data, paragraph_file_path)

                        except Exception as e:
                            self.console.print(f"[red]  Error processing paragraph {i+1} for job {job.job_ulid}: {e}[/red]")
                            # Optionally, mark this paragraph as failed or add an error message
                            paragraph_entry['edited'] = f"[ERROR] {e}"
                            self._save_paragraphs_to_file(paragraphs_data, paragraph_file_path)
                            # Decide whether to continue or break on error
                            # For now, we'll continue to try other paragraphs
                
            if edited_count == 0:
                self.console.print(f"[yellow]No new paragraphs needed editing for job {job.job_ulid}.[/yellow]")
            else:
                self.console.print(f"[green]Finished editing {edited_count} paragraphs for job {job.job_ulid}.[/green]")

            # Check if all paragraphs are now edited
            if all(p.get('edited') is not None for p in paragraphs_data):
                edit_llm_stage = session.query(JobStage).filter(
                    JobStage.job_id == self.job_id,
                    JobStage.stage_name == "edit_local_llm"
                ).first()
                if edit_llm_stage and edit_llm_stage.state != StageState.success:
                    edit_llm_stage.state = StageState.success
                    session.commit()
                    self.console.print(f"[green]Job {job.job_ulid}: 'edit_local_llm' stage marked as SUCCESS.[/green]")
            else:
                self.console.print(f"[yellow]Job {job.job_ulid}: Not all paragraphs are edited. 'edit_local_llm' stage remains pending.[/yellow]")

    def build_paragraph_editing_score(self, original_paragraph_dict, edited_paragraph_dict):
        """
        Compares original and edited paragraphs to build an editing score.
        This isn't actually being used right now, we just have a placeholder for now
        """
        pass
