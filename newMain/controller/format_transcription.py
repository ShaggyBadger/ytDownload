import logging
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt

from pathlib import Path

from database.session_manager import get_session
from database.models import JobInfo, JobStage, StageState
from sqlalchemy import and_
from sqlalchemy.orm import aliased

from services.formatter import Formatter
from config import config

logger = logging.getLogger(__name__)


class FormatTranscriptionController:
    def __init__(self):
        self.console = Console()
        self.formatter = Formatter()
        logger.debug("FormatTranscriptionController initialized.")

    def run(self):
        logger.info("Format Transcription Menu started. Displaying menu.")
        while True:
            self.console.clear()
            self.console.print(
                Panel(
                    Text(
                        "Format Transcription Menu",
                        justify="center",
                        style="bold green",
                    )
                ),
                style="bold green",
            )
            self.console.print(
                "[bold blue]1.[/bold blue] Format All Pending Transcriptions"
            )
            self.console.print(
                "[bold blue]2.[/bold blue] Format Selected Transcription"
            )
            self.console.print("[bold red]b.[/bold red] Back to Main Menu")

            choice = Prompt.ask(
                "[bold green]Choose an option[/bold green]",
                choices=["1", "2", "b"],
                default="b",
            ).lower()
            logger.debug("User selected menu option: '%s'", choice)

            if choice == "1":
                logger.info("User selected 'Format All Pending Transcriptions'.")
                try:
                    self.format_all_transcriptions()
                except Exception:
                    logger.critical(
                        "An unhandled error occurred during 'Format All Pending Transcriptions'.",
                        exc_info=True,
                    )
                    self.console.print(
                        "[red]An unexpected error occurred. Check logs for details.[/red]"
                    )
            elif choice == "2":
                logger.info("User selected 'Format Selected Transcription'.")
                try:
                    self.format_selected_transcription()
                except Exception:
                    logger.critical(
                        "An unhandled error occurred during 'Format Selected Transcription'.",
                        exc_info=True,
                    )
                    self.console.print(
                        "[red]An unexpected error occurred. Check logs for details.[/red]"
                    )
            elif choice == "b":
                logger.info("Exiting Format Transcription Menu. User selected 'Back'.")
                break

            self.console.input("Press Enter to continue...")
        logger.info("Exited Format Transcription Menu.")

    def format_selected_transcription(self):
        logger.info("Starting 'Format Selected Transcription' process.")
        self.console.print(
            Panel(
                Text(
                    "Formatting Selected Transcription",
                    justify="center",
                    style="bold yellow",
                )
            ),
            style="bold yellow",
        )

        job_id_str = Prompt.ask("[bold green]Enter the Job ID to format[/bold green]")
        logger.debug("User entered Job ID for selected transcription: '%s'", job_id_str)
        try:
            job_id = int(job_id_str)
        except ValueError:
            logger.warning("Invalid Job ID entered: '%s'. Not a number.", job_id_str)
            self.console.print(
                "[bold red]Invalid Job ID. Please enter a number.[/bold red]"
            )
            Prompt.ask("Press Enter to continue...")
            return

        with self.console.status(
            f"[bold green]Searching for job {job_id} to format...[/bold green]",
            spinner=config.SPINNER,
        ) as status:
            try:
                with get_session() as session:
                    # Find the specific job by ID, and check its stages
                    logger.debug(
                        f"Querying for Job ID {job_id} with transcribe_whisper success and format_gemini pending."
                    )

                    # Create aliases for JobStage to filter on two different stages for the same JobInfo
                    TranscribeWhisperStage = aliased(JobStage)
                    FormatGeminiStage = aliased(JobStage)

                    job_to_format = (
                        session.query(JobInfo)
                        .filter(JobInfo.id == job_id)
                        .join(TranscribeWhisperStage, JobInfo.stages)
                        .join(FormatGeminiStage, JobInfo.stages)
                        .filter(
                            TranscribeWhisperStage.stage_name == "transcribe_whisper",
                            TranscribeWhisperStage.state == StageState.success,
                            FormatGeminiStage.stage_name == "format_gemini",
                            FormatGeminiStage.state.in_(
                                [StageState.pending, StageState.failed]
                            ),
                        )
                        .first()
                    )

                    if not job_to_format:
                        logger.warning(
                            f"Job ID {job_id} not found or not ready for formatting (transcribe_whisper not success or format_gemini not pending/failed)."
                        )
                        status.update(
                            f"[bold red]Job ID {job_id} not found or not ready for formatting.[/bold red]"
                        )
                        self.console.print(
                            f"[red]Job ID {job_id} not found, or its 'transcribe_whisper' stage is not successful, or 'format_gemini' is not pending/failed.[/red]"
                        )
                        Prompt.ask("Press Enter to continue...")
                        return

                    job = job_to_format  # for clarity
                    logger.info(
                        f"Found job {job.job_ulid} (ID: {job.id}) ready for formatting."
                    )
                    self.console.print(
                        f"[bold green]Found job [cyan]{job.job_ulid}[/cyan] ready for formatting.[/bold green]"
                    )
                    status.update(
                        f"[bold green]Processing transcription for job [cyan]{job.job_ulid}[/cyan]...[/bold green]"
                    )

                    whisper_stage = next(
                        (s for s in job.stages if s.stage_name == "transcribe_whisper"),
                        None,
                    )
                    format_gemini_stage = next(
                        (s for s in job.stages if s.stage_name == "format_gemini"), None
                    )

                    if (
                        not whisper_stage
                        or not whisper_stage.output_path
                        or not Path(whisper_stage.output_path).exists()
                    ):
                        logger.error(
                            f"Missing transcribe_whisper output, output path, or file not found for job {job.job_ulid}."
                        )
                        self.console.print(
                            f"[bold red]Error: No successful 'transcribe_whisper' stage, output path missing, or transcript file not found for job [cyan]{job.job_ulid}[/cyan]. Skipping.[/bold red]"
                        )
                        if format_gemini_stage:
                            format_gemini_stage.state = StageState.failed
                            format_gemini_stage.last_error = (
                                "Missing transcribe_whisper output or file not found."
                            )
                            session.add(format_gemini_stage)
                            session.commit()
                            logger.info(
                                f"Updated format_gemini stage to FAILED for Job {job.job_ulid} due to missing whisper output."
                            )
                        Prompt.ask("Press Enter to continue...")
                        return

                    if not format_gemini_stage:
                        logger.error(
                            f"'format_gemini' stage not found for job {job.job_ulid}. Skipping."
                        )
                        self.console.print(
                            f"[bold red]Error: 'format_gemini' stage not found for job [cyan]{job.job_ulid}[/cyan]. Skipping.[/bold red]"
                        )
                        Prompt.ask("Press Enter to continue...")
                        return

                    try:
                        logger.info(
                            f"Calling Formatter service for Job ULID: {job.job_ulid}."
                        )
                        output_file_path = self.formatter.run(
                            job_directory=Path(job.job_directory),
                            input_file_path=Path(whisper_stage.output_path),
                        )

                        if output_file_path is None:
                            logger.warning(
                                f"Formatter returned None for job {job.job_ulid}. Marking as failed."
                            )
                            status.update(
                                f"[yellow]Skipping job [cyan]{job.job_ulid}[/cyan] due to formatting failure.[/yellow]"
                            )
                            format_gemini_stage.state = StageState.failed
                            format_gemini_stage.last_error = "Formatting failed: Gemini API quota exceeded, API error, or excessive word loss after retries."
                            session.add(format_gemini_stage)
                            session.commit()
                            logger.info(
                                f"Updated format_gemini stage to FAILED for Job {job.job_ulid} in DB."
                            )
                        else:
                            format_gemini_stage.state = StageState.success
                            format_gemini_stage.output_path = str(output_file_path)
                            session.add(format_gemini_stage)
                            session.commit()
                            logger.info(
                                f"Successfully formatted and saved for job {job.job_ulid}. Output path: {output_file_path}."
                            )
                            self.console.print(
                                f"[bold green]Successfully formatted and saved for job [cyan]{job.job_ulid}[/cyan].[/bold green]"
                            )

                    except RuntimeError as e:
                        logger.error(
                            f"RuntimeError during formatting for job {job.job_ulid}: {e}",
                            exc_info=True,
                        )
                        self.console.print(
                            f"[bold red]Failed to format transcription for job [cyan]{job.job_ulid}[/cyan]: {e}[/bold red]"
                        )
                        format_gemini_stage.state = StageState.failed
                        format_gemini_stage.last_error = str(e)
                        session.add(format_gemini_stage)
                        session.commit()
                        logger.info(
                            f"Updated format_gemini stage to FAILED for Job {job.job_ulid} in DB due to RuntimeError."
                        )
                    except Exception as e:
                        logger.critical(
                            f"An unexpected error occurred during formatting for job {job.job_ulid}: {e}",
                            exc_info=True,
                        )
                        self.console.print(
                            f"[bold red]An unexpected error occurred for job [cyan]{job.job_ulid}[/cyan]: {e}[/bold red]"
                        )
                        format_gemini_stage.state = StageState.failed
                        format_gemini_stage.last_error = str(e)
                        session.add(format_gemini_stage)
                        session.commit()
                        logger.info(
                            f"Updated format_gemini stage to FAILED for Job {job.job_ulid} in DB due to unexpected error."
                        )

            except Exception as e:
                logger.critical(
                    f"An error occurred during transcription formatting selection process: {e}",
                    exc_info=True,
                )
                status.update(
                    f"[bold red]An error occurred during transcription formatting: {e}[/bold red]"
                )
                self.console.print(
                    f"[bold red]An error occurred during transcription formatting: {e}[/bold red]"
                )

        Prompt.ask("Press Enter to continue...")

    def format_all_transcriptions(self):
        logger.info("Starting 'Format All Pending Transcriptions' process.")
        self.console.print(
            Panel(
                Text(
                    "Formatting All Pending Transcriptions",
                    justify="center",
                    style="bold yellow",
                )
            ),
            style="bold yellow",
        )

        with self.console.status(
            "[bold green]Searching for transcriptions to format...[/bold green]",
            spinner=config.SPINNER,
        ) as status:
            try:
                with get_session() as session:
                    # Query for jobs where transcribe_whisper is successful AND format_gemini is pending
                    logger.debug(
                        "Querying for jobs with transcribe_whisper success and format_gemini pending/failed."
                    )

                    # Create aliases for JobStage to filter on two different stages for the same JobInfo
                    TranscribeWhisperStage = aliased(JobStage)
                    FormatGeminiStage = aliased(JobStage)

                    jobs_to_format = (
                        session.query(JobInfo)
                        .join(TranscribeWhisperStage, JobInfo.stages)
                        .join(FormatGeminiStage, JobInfo.stages)
                        .filter(
                            TranscribeWhisperStage.stage_name == "transcribe_whisper",
                            TranscribeWhisperStage.state == StageState.success,
                            FormatGeminiStage.stage_name == "format_gemini",
                            FormatGeminiStage.state.in_(
                                [StageState.pending, StageState.failed]
                            ),
                        )
                        .all()
                    )

                    if not jobs_to_format:
                        logger.info(
                            "No transcriptions found ready for formatting (transcribe_whisper success and format_gemini pending/failed)."
                        )
                        status.update(
                            "[bold green]No transcriptions found ready for formatting.[/bold green]"
                        )
                        self.console.print(
                            "[green]No transcriptions found ready for formatting.[/green]"
                        )
                        return

                    logger.info(
                        f"Found {len(jobs_to_format)} transcriptions to format."
                    )
                    self.console.print(
                        f"[bold green]Found {len(jobs_to_format)} transcriptions to format.[/bold green]"
                    )
                    for i, job in enumerate(jobs_to_format):
                        status.update(
                            f"[bold green]Processing transcription {i + 1}/{len(jobs_to_format)} for job [cyan]{job.job_ulid}[/cyan]...[/bold green]"
                        )
                        logger.info(
                            f"Processing transcription {i + 1}/{len(jobs_to_format)} for Job ULID: {job.job_ulid} (ID: {job.id})."
                        )

                        whisper_stage = next(
                            (
                                s
                                for s in job.stages
                                if s.stage_name == "transcribe_whisper"
                            ),
                            None,
                        )
                        format_gemini_stage = next(
                            (s for s in job.stages if s.stage_name == "format_gemini"),
                            None,
                        )

                        if (
                            not whisper_stage
                            or not whisper_stage.output_path
                            or not Path(whisper_stage.output_path).exists()
                        ):
                            logger.error(
                                f"Missing transcribe_whisper output, output path, or file not found for job {job.job_ulid}. Skipping."
                            )
                            self.console.print(
                                f"[bold red]Error: No successful 'transcribe_whisper' stage, output path missing, or transcript file not found for job [cyan]{job.job_ulid}[/cyan]. Skipping.[/bold red]"
                            )
                            if format_gemini_stage:
                                format_gemini_stage.state = StageState.failed
                                format_gemini_stage.last_error = "Missing transcribe_whisper output or file not found."
                                session.add(format_gemini_stage)
                                session.commit()
                                logger.info(
                                    f"Updated format_gemini stage to FAILED for Job {job.job_ulid} due to missing whisper output."
                                )
                            continue

                        if not format_gemini_stage:
                            logger.error(
                                f"'format_gemini' stage not found for job {job.job_ulid}. Skipping."
                            )
                            self.console.print(
                                f"[bold red]Error: 'format_gemini' stage not found for job [cyan]{job.job_ulid}[/cyan]. Skipping.[/bold red]"
                            )
                            continue

                        try:
                            logger.info(
                                f"Calling Formatter service for Job ULID: {job.job_ulid}."
                            )
                            output_file_path = self.formatter.run(
                                job_directory=Path(job.job_directory),
                                input_file_path=Path(whisper_stage.output_path),
                            )

                            if output_file_path is None:
                                logger.warning(
                                    f"Formatter returned None for job {job.job_ulid}. Marking as failed and stopping all further processing."
                                )
                                status.update(
                                    f"[yellow]Stopping all further formatting for [cyan]{job.job_ulid}[/cyan] due to critical failure (e.g., Gemini quota).[/yellow]"
                                )
                                self.console.print(
                                    "[bold red]Critical error encountered (e.g., Gemini API quota exceeded). Stopping all further formatting tasks.[/bold red]"
                                )
                                format_gemini_stage.state = StageState.failed
                                format_gemini_stage.last_error = "Formatting failed: Gemini API quota exceeded, API error, or excessive word loss after retries. Processing halted."
                                session.add(format_gemini_stage)
                                session.commit()
                                logger.info(
                                    f"Updated format_gemini stage to FAILED for Job {job.job_ulid} in DB and breaking loop."
                                )
                                break  # <--- THIS IS THE KEY CHANGE: Stop the loop

                            format_gemini_stage.state = StageState.success
                            format_gemini_stage.output_path = str(output_file_path)
                            session.add(format_gemini_stage)
                            session.commit()
                            logger.info(
                                f"Successfully formatted and saved for job {job.job_ulid}. Output path: {output_file_path}."
                            )
                            self.console.print(
                                f"[bold green]Successfully formatted and saved for job [cyan]{job.job_ulid}[/cyan].[/bold green]"
                            )

                        except RuntimeError as e:
                            logger.error(
                                f"RuntimeError during formatting for job {job.job_ulid}: {e}",
                                exc_info=True,
                            )
                            self.console.print(
                                f"[bold red]Failed to format transcription for job [cyan]{job.job_ulid}[/cyan]: {e}[/bold red]"
                            )
                            format_gemini_stage.state = StageState.failed
                            format_gemini_stage.last_error = str(e)
                            session.add(format_gemini_stage)
                            session.commit()
                            logger.info(
                                f"Updated format_gemini stage to FAILED for Job {job.job_ulid} in DB due to RuntimeError."
                            )
                            continue
                        except Exception as e:
                            logger.critical(
                                f"An unexpected error occurred during formatting for job {job.job_ulid}: {e}",
                                exc_info=True,
                            )
                            self.console.print(
                                f"[bold red]An unexpected error occurred for job [cyan]{job.job_ulid}[/cyan]: {e}[/bold red]"
                            )
                            format_gemini_stage.state = StageState.failed
                            format_gemini_stage.last_error = str(e)
                            session.add(format_gemini_stage)
                            session.commit()
                            logger.info(
                                f"Updated format_gemini stage to FAILED for Job {job.job_ulid} in DB due to unexpected error."
                            )
                            continue

                    status.update(
                        "[bold green]Finished processing all pending transcriptions.[/bold green]"
                    )
                    self.console.print(
                        "[green]All pending transcriptions have been processed.[/green]"
                    )
            except Exception as e:
                logger.critical(
                    f"An error occurred during the 'Format All Pending Transcriptions' process: {e}",
                    exc_info=True,
                )
                status.update(
                    f"[bold red]An error occurred during transcription formatting: {e}[/bold red]"
                )
                self.console.print(
                    f"[bold red]An error occurred during transcription formatting: {e}[/bold red]"
                )

        Prompt.ask("Press Enter to continue...")
