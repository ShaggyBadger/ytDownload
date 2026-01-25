from pathlib import Path
import json

from joshlib.gemini import GeminiClient
from rich.console import Console # Import Console

from config import config
from database.models import JobInfo, JobStage, StageState, STAGE_ORDER
from database.session_manager import get_session


class GenerateMetadata:
    """
    This class handles the metadata extraction for a given job.
    It fetches job details, updates the stage status, generates metadata
    using an LLM, saves it as a JSON file, and updates the job stage accordingly.
    """
    def __init__(self, job_id: int, console: Console): # Accept console object
        self.job_id = job_id
        self.console = console # Store console object
        self.prompts_dir = Path(__file__).parent / 'prompts' / 'metadata'
        self.llm_client = GeminiClient()


    def process_job(self):
        with get_session() as session:
            job_info = session.query(JobInfo).filter_by(id=self.job_id).first()
            if not job_info:
                self.console.print(f"[bold red]Job with ID {self.job_id} not found.[/bold red]")
                return

            metadata_stage = session.query(JobStage).filter_by(
                job_id=self.job_id,
                stage_name="extract_metadata"
            ).first()

            if not metadata_stage:
                self.console.print(f"[bold red]Metadata stage not found for Job ID {self.job_id}.[/bold red]")
                return

            try:
                self.console.print(f"[yellow]Updating stage status to 'running' for Job ID {self.job_id}...[/yellow]")
                metadata_stage.state = StageState.running
                session.add(metadata_stage)
                session.commit()
                session.refresh(metadata_stage)
                self.console.print(f"[green]Stage status updated to 'running'.[/green]")

                self.console.print(f"[yellow]Retrieving formatted transcript path for Job ID {self.job_id}...[/yellow]")
                formatted_transcript_stage_name = STAGE_ORDER[STAGE_ORDER.index("extract_metadata") - 1]
                formatted_transcript_stage = session.query(JobStage).filter_by(
                    job_id=self.job_id,
                    stage_name=formatted_transcript_stage_name
                ).first()

                if not formatted_transcript_stage or formatted_transcript_stage.state != StageState.success or not formatted_transcript_stage.output_path:
                    raise FileNotFoundError(f"Formatted transcript not found or not successful for stage {formatted_transcript_stage_name} of Job ID {self.job_id}")

                formatted_transcript_path = Path(formatted_transcript_stage.output_path)
                if not formatted_transcript_path.is_file():
                    raise FileNotFoundError(f"Formatted transcript file not found at {formatted_transcript_path} for Job ID {self.job_id}")
                self.console.print(f"[green]Formatted transcript found at: {formatted_transcript_path}[/green]")

                self.console.print(f"[yellow]Starting metadata generation for Job ID {self.job_id}...[/yellow]")
                metadata_output_path = self._gen_metadata_logic(job_info, formatted_transcript_path)
                self.console.print(f"[green]Metadata generation complete. Output saved to: {metadata_output_path}[/green]")

                self.console.print(f"[yellow]Updating stage status to 'success' for Job ID {self.job_id}...[/yellow]")
                metadata_stage.state = StageState.success
                metadata_stage.output_path = str(metadata_output_path)
                session.add(metadata_stage)
                session.commit()
                self.console.print(f"[bold green]Successfully extracted metadata for Job ID {self.job_id}[/bold green]")

            except Exception as e:
                session.rollback()
                metadata_stage.state = StageState.failed
                metadata_stage.last_error = str(e)
                session.add(metadata_stage)
                session.commit()
                self.console.print(f"[bold red]Failed to extract metadata for Job ID {self.job_id}: {e}[/bold red]")

    def _gen_metadata_logic(self, job_info: JobInfo, formatted_transcript_path: Path) -> Path:
        """
        Logic for the metadata generation stage.
        Reads the formatted transcript, generates metadata using LLM,
        and saves it as a JSON file in the job's directory.
        """
        self.console.print(f"[yellow]Reading formatted transcript from {formatted_transcript_path}...[/yellow]")
        with open(formatted_transcript_path, 'r') as f:
            text_for_metadata = f.read()
        self.console.print("[green]Formatted transcript read.[/green]")

        metadata_dict = {}

        metadata_que = {
            'title': 'generate-title.txt',
            'thesis': 'generate-thesis.txt',
            'summary': 'generate-summary.txt',
            'outline': 'generate-outline.txt',
            'tone': 'generate-tone.txt',
            'references': 'generate-references.txt'
        }
        self.console.print("[yellow]Generating metadata using LLM...[/yellow]")
        for category, file_name in metadata_que.items():
            self.console.print(f"[blue]  - Generating {category}...[/blue]")
            prompt_path = self.prompts_dir / file_name
            prompt_template = prompt_path.read_text()
            prompt = prompt_template.format(SERMON_TEXT=text_for_metadata)
            metadata = self.llm_client.submit_prompt(prompt)
            metadata_dict[category] = metadata
            self.console.print(f"[green]  - {category} generated.[/green]")

        job_dir = Path(job_info.job_directory)
        metadata_filename = config.METADATA_FILE_NAME
        metadata_output_path = job_dir / metadata_filename

        self.console.print(f"[yellow]Saving generated metadata to {metadata_output_path}...[/yellow]")
        with open(metadata_output_path, 'w') as f:
            json.dump(metadata_dict, f, indent=4)
        self.console.print(f"[green]Metadata saved.[/green]")

        return metadata_output_path
