from pathlib import Path
import json

from rich.console import Console

from database.session_manager import get_session
from database.models import JobInfo, JobStage, StageState
from config import config

class ChapterBuilder:
    """Class to handle building the final chapter document."""

    def __init__(self, job_id):
        """A class to handle building the final chapter document for a job."""
        self.job_id = job_id
        self.console = Console()

    def build_chapter_document(self):
        """
        Builds the final chapter document from metadata and edited paragraphs.
        """
        with get_session() as session:
            job = session.query(JobInfo).filter(JobInfo.id == self.job_id).first()
            if not job:
                self.console.print(f"[red]Job with ID {self.job_id} not found.[/red]")
                return

            self.console.print(f"Building chapter document for job: {job.job_ulid}")

            job_directory = Path(job.job_directory)
            
            # --- Load Metadata ---
            metadata_path = job_directory / config.METADATA_FILE_NAME
            metadata = {}
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                except Exception as e:
                    self.console.print(f"[red]Error loading metadata from {metadata_path}: {e}[/red]")
                    return
            else:
                self.console.print(f"[red]Metadata file not found for job {job.job_ulid} at {metadata_path}.[/red]")
                return

            title = metadata.get('title', 'Untitled Chapter')
            thesis = metadata.get('thesis', 'No thesis provided.')
            summary = metadata.get('summary', 'No summary provided.')

            # --- Load Edited Paragraphs ---
            paragraph_json_path = job_directory / config.PARAGRAPHS_FILE_NAME
            paragraphs_data = []
            if paragraph_json_path.exists():
                try:
                    with open(paragraph_json_path, 'r') as f:
                        paragraphs_data = json.load(f)
                except Exception as e:
                    self.console.print(f"[red]Error loading paragraphs from {paragraph_json_path}: {e}[/red]")
                    return
            else:
                self.console.print(f"[red]Paragraphs JSON file not found for job {job.job_ulid} at {paragraph_json_path}.[/red]")
                return
            
            # Ensure all paragraphs are edited before proceeding
            if any(p.get('edited') is None for p in paragraphs_data):
                self.console.print(f"[red]Not all paragraphs for job {job.job_ulid} are edited. Cannot build chapter.[/red]")
                return

            edited_content = "\n\n".join([p['edited'] for p in paragraphs_data if p.get('edited')])

            # --- Construct Final Document ---
            final_document_content = f"# {title}\n\n"
            final_document_content += f"**Thesis:** {thesis}\n\n"
            final_document_content += f"**Summary:** {summary}\n\n"
            final_document_content += "## Edited Content\n\n"
            final_document_content += edited_content

            # --- Save Final Document ---
            final_document_path = job_directory / config.FINAL_DOCUMENT_NAME
            try:
                with open(final_document_path, 'w') as f:
                    f.write(final_document_content)
                self.console.print(f"[green]Successfully built chapter document at {final_document_path}[/green]")
            except Exception as e:
                self.console.print(f"[red]Error saving final document to {final_document_path}: {e}[/red]")
                return

            # --- Update Database Stage ---
            build_chapter_stage = session.query(JobStage).filter(
                JobStage.job_id == self.job_id,
                JobStage.stage_name == "build_chapter"
            ).first()

            if build_chapter_stage:
                build_chapter_stage.output_path = str(final_document_path)
                build_chapter_stage.state = StageState.success
                session.commit()
                self.console.print(f"[green]Job {job.job_ulid}: 'build_chapter' stage marked as SUCCESS.[/green]")
            else:
                self.console.print(f"[yellow]Job {job.job_ulid}: 'build_chapter' stage not found in database.[/yellow]")
