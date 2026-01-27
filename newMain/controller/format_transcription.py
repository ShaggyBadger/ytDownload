from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt

from pathlib import Path

from database.session_manager import get_session
from database.models import JobInfo, JobStage, StageState
from sqlalchemy import and_

from services.formatter import Formatter
from config import config

class FormatTranscriptionController:
    def __init__(self):
        self.console = Console()
        self.formatter = Formatter()

    def run(self):
        while True:
            self.console.clear()
            self.console.print(Panel(Text("Format Transcription Menu", justify="center", style="bold green")), style="bold green")
            self.console.print("[bold blue]1.[/bold blue] Format All Pending Transcriptions")
            self.console.print("[bold blue]2.[/bold blue] Format Selected Transcription")
            self.console.print("[bold red]b.[/bold red] Back to Main Menu")

            choice = Prompt.ask("[bold green]Choose an option[/bold green]", choices=["1", "2", "b"], default="b").lower()

            if choice == "1":
                self.format_all_transcriptions()
            elif choice == "2":
                self.format_selected_transcription()
            elif choice == "b":
                break

    def format_selected_transcription(self):
        self.console.print(Panel(Text("Formatting Selected Transcription", justify="center", style="bold yellow")), style="bold yellow")
        
        job_id_str = Prompt.ask("[bold green]Enter the Job ID to format[/bold green]")
        try:
            job_id = int(job_id_str)
        except ValueError:
            self.console.print("[bold red]Invalid Job ID. Please enter a number.[/bold red]")
            Prompt.ask("Press Enter to continue...")
            return

        with self.console.status(f"[bold green]Searching for job {job_id} to format...[/bold green]", spinner=config.SPINNER) as status:
            try:
                with get_session() as session:
                    # Find the specific job by ID, and check its stages
                    job_to_format = (
                        session.query(JobInfo)
                        .filter(JobInfo.id == job_id)
                        .join(JobInfo.stages)
                        .filter(JobStage.stage_name == "transcribe_whisper", JobStage.state == StageState.success)
                        .filter(JobInfo.stages.any(
                            and_(
                                JobStage.stage_name == "format_gemini",
                                (JobStage.state == StageState.pending) | (JobStage.state == StageState.failed) | (JobStage.state == StageState.success)
                            )
                        ))
                        .first()
                    )

                    if not job_to_format:
                        status.update(f"[bold red]Job ID {job_id} not found or not ready for formatting.[/bold red]")
                        self.console.print(f"[red]Job ID {job_id} not found, or its 'transcribe_whisper' stage is not successful, or 'format_gemini' is not pending/failed.[/red]")
                        Prompt.ask("Press Enter to continue...")
                        return

                    job = job_to_format # for clarity
                    self.console.print(f"[bold green]Found job [cyan]{job.job_ulid}[/cyan] ready for formatting.[/bold green]")
                    status.update(f"[bold green]Processing transcription for job [cyan]{job.job_ulid}[/cyan]...[/bold green]")
                    
                    whisper_stage = next((s for s in job.stages if s.stage_name == "transcribe_whisper"), None)
                    format_gemini_stage = next((s for s in job.stages if s.stage_name == "format_gemini"), None)

                    if not whisper_stage or not whisper_stage.output_path or not Path(whisper_stage.output_path).exists():
                        self.console.print(f"[bold red]Error: No successful 'transcribe_whisper' stage, output path missing, or transcript file not found for job [cyan]{job.job_ulid}[/cyan]. Skipping.[/bold red]")
                        if format_gemini_stage:
                            format_gemini_stage.state = StageState.failed
                            format_gemini_stage.last_error = "Missing transcribe_whisper output or file not found."
                            session.add(format_gemini_stage)
                            session.commit()
                        Prompt.ask("Press Enter to continue...")
                        return

                    if not format_gemini_stage:
                        self.console.print(f"[bold red]Error: 'format_gemini' stage not found for job [cyan]{job.job_ulid}[/cyan]. Skipping.[/bold red]")
                        Prompt.ask("Press Enter to continue...")
                        return

                    try:
                        # Call the Formatter's run method
                        output_file_path = self.formatter.run(
                            job_directory=Path(job.job_directory),
                            input_file_path=Path(whisper_stage.output_path)
                        )

                        if output_file_path is None:
                            status.update(f"[yellow]Skipping job [cyan]{job.job_ulid}[/cyan] due to formatting failure.[/yellow]")
                            format_gemini_stage.state = StageState.failed # Mark as failed for quota or excessive word loss
                            format_gemini_stage.last_error = "Formatting failed: Gemini API quota exceeded, API error, or excessive word loss after retries."
                            session.add(format_gemini_stage)
                            session.commit()
                        else:
                            format_gemini_stage.state = StageState.success
                            format_gemini_stage.output_path = str(output_file_path)
                            session.add(format_gemini_stage)
                            session.commit()
                            self.console.print(f"[bold green]Successfully formatted and saved for job [cyan]{job.job_ulid}[/cyan].[/bold green]")

                    except RuntimeError as e:
                        self.console.print(f"[bold red]Failed to format transcription for job [cyan]{job.job_ulid}[/cyan]: {e}[/bold red]")
                        format_gemini_stage.state = StageState.failed
                        format_gemini_stage.last_error = str(e)
                        session.add(format_gemini_stage)
                        session.commit()
                    except Exception as e:
                        self.console.print(f"[bold red]An unexpected error occurred for job [cyan]{job.job_ulid}[/cyan]: {e}[/bold red]")
                        format_gemini_stage.state = StageState.failed
                        format_gemini_stage.last_error = str(e)
                        session.add(format_gemini_stage)
                        session.commit()
                
            except Exception as e:
                status.update(f"[bold red]An error occurred during transcription formatting: {e}[/bold red]")
                self.console.print(f"[bold red]An error occurred during transcription formatting: {e}[/bold red]")
        
        Prompt.ask("Press Enter to continue...")

    def format_all_transcriptions(self):
        self.console.print(Panel(Text("Formatting All Pending Transcriptions", justify="center", style="bold yellow")), style="bold yellow")

        with self.console.status("[bold green]Searching for transcriptions to format...[/bold green]", spinner=config.SPINNER) as status:
            try:
                with get_session() as session:
                    # Find jobs where transcribe_whisper is successful and format_gemini is pending/failed
                    jobs_to_format = (
                        session.query(JobInfo)
                        .join(JobInfo.stages)
                        .filter(JobStage.stage_name == "transcribe_whisper", JobStage.state == StageState.success)
                        .filter(JobInfo.stages.any(
                            and_(
                                JobStage.stage_name == "format_gemini",
                                (JobStage.state == StageState.pending) | (JobStage.state == StageState.failed) | (JobStage.state == StageState.success)
                            )
                        ))
                        .all()
                    )

                    if not jobs_to_format:
                        status.update("[bold green]No transcriptions found ready for formatting.[/bold green]")
                        self.console.print("[green]No transcriptions found ready for formatting.[/green]")
                        return

                    self.console.print(f"[bold green]Found {len(jobs_to_format)} transcriptions to format.[/bold green]")
                    for i, job in enumerate(jobs_to_format):
                        status.update(f"[bold green]Processing transcription {i + 1}/{len(jobs_to_format)} for job [cyan]{job.job_ulid}[/cyan]...[/bold green]")
                        
                        whisper_stage = next((s for s in job.stages if s.stage_name == "transcribe_whisper"), None)
                        format_gemini_stage = next((s for s in job.stages if s.stage_name == "format_gemini"), None)

                        if not whisper_stage or not whisper_stage.output_path or not Path(whisper_stage.output_path).exists():
                            self.console.print(f"[bold red]Error: No successful 'transcribe_whisper' stage, output path missing, or transcript file not found for job [cyan]{job.job_ulid}[/cyan]. Skipping.[/bold red]")
                            if format_gemini_stage:
                                format_gemini_stage.state = StageState.failed
                                format_gemini_stage.last_error = "Missing transcribe_whisper output or file not found."
                                session.add(format_gemini_stage)
                                session.commit()
                            continue

                        if not format_gemini_stage:
                            self.console.print(f"[bold red]Error: 'format_gemini' stage not found for job [cyan]{job.job_ulid}[/cyan]. Skipping.[/bold red]")
                            continue

                        try:
                            # Call the Formatter's run method
                            output_file_path = self.formatter.run(
                                job_directory=Path(job.job_directory),
                                input_file_path=Path(whisper_stage.output_path)
                            )

                            if output_file_path is None:
                                status.update(f"[yellow]Skipping job [cyan]{job.job_ulid}[/cyan] due to formatting failure.[/yellow]")
                                format_gemini_stage.state = StageState.failed # Mark as failed for quota or excessive word loss
                                format_gemini_stage.last_error = "Formatting failed: Gemini API quota exceeded, API error, or excessive word loss after retries."
                                session.add(format_gemini_stage)
                                session.commit()
                                continue

                            format_gemini_stage.state = StageState.success
                            format_gemini_stage.output_path = str(output_file_path)
                            session.add(format_gemini_stage)
                            session.commit()
                            self.console.print(f"[bold green]Successfully formatted and saved for job [cyan]{job.job_ulid}[/cyan].[/bold green]")

                        except RuntimeError as e:
                            self.console.print(f"[bold red]Failed to format transcription for job [cyan]{job.job_ulid}[/cyan]: {e}[/bold red]")
                            format_gemini_stage.state = StageState.failed
                            format_gemini_stage.last_error = str(e)
                            session.add(format_gemini_stage)
                            session.commit()
                        except Exception as e:
                            self.console.print(f"[bold red]An unexpected error occurred for job [cyan]{job.job_ulid}[/cyan]: {e}[/bold red]")
                            format_gemini_stage.state = StageState.failed
                            format_gemini_stage.last_error = str(e)
                            session.add(format_gemini_stage)
                            session.commit()
                    status.update("[bold green]Finished processing all pending transcriptions.[/bold green]")
                    self.console.print("[green]All pending transcriptions have been processed.[/green]")
            except Exception as e:
                status.update(f"[bold red]An error occurred during transcription formatting: {e}[/bold red]")
                self.console.print(f"[bold red]An error occurred during transcription formatting: {e}[/bold red]")
        
        Prompt.ask("Press Enter to continue...")