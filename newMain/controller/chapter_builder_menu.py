import logging
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from sqlalchemy.orm import joinedload
from pathlib import Path
import json

from database.session_manager import get_session
from database.models import JobInfo, VideoInfo, JobStage, StageState
from services.chapter_builder import ChapterBuilder
from config import config

logger = logging.getLogger(__name__)


class ChapterBuilderMenu:
    def __init__(self):
        self.console = Console()
        self.options = {
            "1": {
                "desc": "Build chapter for single job (if missing)",
                "func": self._select_and_build_single_chapter,
            },
            "2": {
                "desc": "Build chapter for all eligible jobs (if missing)",
                "func": self._build_all_chapters,
            },
            "3": {
                "desc": "Overwrite chapter document by ULID",
                "func": self._overwrite_chapter_document,
            },
            "b": {"desc": "Back to Main Menu", "func": None},
        }
        logger.debug("ChapterBuilderMenu initialized with options: %s", self.options)

    def _get_eligible_jobs_for_chapter_build(self):
        """
        Queries the database for jobs that have successfully completed the 'edit_local_llm' stage,
        and where the final document does not exist on disk.
        Returns a list of dictionaries, each containing relevant job information.
        """
        logger.debug("Querying for eligible jobs for chapter building.")
        jobs_list = []
        try:
            with get_session() as session:
                # Subquery to find jobs where edit_local_llm is successful
                successful_edit_llm_jobs = (
                    session.query(JobStage.job_id)
                    .filter(
                        JobStage.stage_name == "edit_local_llm",
                        JobStage.state == StageState.success,
                    )
                    .subquery()
                )
                logger.debug("Subquery for successful 'edit_local_llm' jobs executed.")

                # Query for jobs that are in the successful_edit_llm_jobs list
                candidate_jobs_query = (
                    (
                        session.query(
                            JobInfo.id.label("job_id"),
                            JobInfo.job_ulid.label("job_ulid"),
                            JobInfo.job_directory.label("job_directory"),
                            VideoInfo.title.label("title"),
                            JobStage.state.label("build_chapter_stage_state"),
                        )
                        .join(VideoInfo, JobInfo.video_id == VideoInfo.id)
                        .join(JobStage, JobInfo.id == JobStage.job_id)
                        .filter(
                            JobInfo.id == successful_edit_llm_jobs.c.job_id,
                            JobStage.stage_name == "build_chapter",
                        )
                    )
                    .distinct()
                    .all()
                )
                logger.debug(
                    f"Found {len(candidate_jobs_query)} candidate jobs from DB query."
                )

                for job_data in candidate_jobs_query:
                    job_directory = Path(job_data.job_directory)
                    final_document_path = job_directory / config.FINAL_DOCUMENT_NAME

                    final_document_exists = final_document_path.exists()
                    logger.debug(
                        f"Job ULID {job_data.job_ulid}: Final document exists on disk: {final_document_exists}"
                    )

                    if not final_document_exists:
                        jobs_list.append(
                            {
                                "id": job_data.job_id,
                                "job_ulid": job_data.job_ulid,
                                "title": job_data.title,
                                "job_directory": job_data.job_directory,
                                "final_document_disk_path": str(final_document_path),
                                "build_chapter_stage_state": job_data.build_chapter_stage_state.value,
                            }
                        )
            logger.info(
                f"Identified {len(jobs_list)} eligible jobs for chapter building."
            )
        except Exception:
            logger.error(
                "Error querying for eligible jobs for chapter build.", exc_info=True
            )
        return jobs_list

    def _select_and_build_single_chapter(self):
        """
        Allows the user to select a single job eligible for chapter building
        and triggers the chapter building process.
        """
        logger.info("Initiating single chapter build selection process.")
        self.console.clear()
        self.console.rule("[bold blue]Select Sermon for Chapter Build[/bold blue]")

        jobs_to_build = self._get_eligible_jobs_for_chapter_build()

        if not jobs_to_build:
            logger.info("No sermons found eligible for single chapter building.")
            self.console.print(
                "[yellow]No sermons found eligible for chapter building.[/yellow]"
            )
            self.console.print(
                "[dim]A sermon must have completed the 'edit_local_llm' stage and not yet have a final document.[/dim]"
            )
            self.console.input("Press Enter to continue...")
            return

        table = Table(
            title="Available Sermons for Chapter Building",
            show_header=True,
            header_style="bold magenta",
            box=config.BOX_STYLE,
            padding=(0, 2),
        )
        table.add_column("No.", style="cyan", width=5)
        table.add_column("Job ULID", style="green")
        table.add_column("Title", style="green")
        table.add_column("Final Document Path", style="dim")
        table.add_column("Build Chapter Status", style="yellow")

        job_map = {}
        for i, job_data in enumerate(jobs_to_build):
            display_num = str(i + 1)
            job_map[display_num] = job_data
            table.add_row(
                display_num,
                job_data["job_ulid"],
                job_data["title"],
                job_data["final_document_disk_path"],
                job_data["build_chapter_stage_state"],
            )

        self.console.print(table)

        while True:
            choice = (
                Prompt.ask(
                    "[bold yellow]Select a sermon by number (or 'b' to go back)[/bold yellow]"
                )
                .strip()
                .lower()
            )
            logger.debug("User selected: '%s'", choice)
            if choice == "b":
                logger.info(
                    "User opted to go back from single chapter build selection."
                )
                return

            selected_job_data = job_map.get(choice)
            if selected_job_data:
                self.console.print(
                    f"[cyan]Selected Job:[/cyan] {selected_job_data['job_ulid']} - [dim]{selected_job_data['title']}[/dim]"
                )
                logger.info(
                    f"User selected Job ULID: {selected_job_data['job_ulid']} (ID: {selected_job_data['id']}) for single chapter build."
                )
                try:
                    chapter_builder_service = ChapterBuilder(
                        job_id=selected_job_data["id"]
                    )
                    chapter_builder_service.build_chapter_document()
                    logger.info(
                        f"Successfully built chapter document for Job ULID: {selected_job_data['job_ulid']}."
                    )
                except Exception:
                    logger.error(
                        f"Error building chapter document for Job ULID: {selected_job_data['job_ulid']}.",
                        exc_info=True,
                    )
                self.console.input("Press Enter to continue...")
                return
            else:
                logger.warning(
                    "Invalid selection for single chapter build: '%s'", choice
                )
                self.console.print(
                    "[red]Invalid selection. Please enter a valid number or 'b'.[/red]"
                )

    def _build_all_chapters(self):
        """
        Builds the final chapter document for all jobs eligible for chapter building.
        """
        logger.info("Initiating bulk chapter build for all eligible jobs.")
        self.console.clear()
        self.console.rule(
            "[bold blue]Building Chapters for All Eligible Jobs[/bold blue]"
        )

        jobs_to_build = self._get_eligible_jobs_for_chapter_build()

        if not jobs_to_build:
            logger.info("No eligible jobs found for bulk chapter building.")
            self.console.print(
                "[yellow]No eligible jobs found for chapter building.[/yellow]"
            )
            self.console.input("Press Enter to continue...")
            return

        self.console.print(f"[cyan]Found {len(jobs_to_build)} eligible jobs.[/cyan]")
        logger.info(
            f"Found {len(jobs_to_build)} eligible jobs for bulk chapter building."
        )
        for i, job_data in enumerate(jobs_to_build):
            self.console.print(
                f"[bold white]Processing Job ({i+1}/{len(jobs_to_build)}):[/bold white] {job_data['job_ulid']} - {job_data['title']}"
            )
            logger.info(
                f"Processing Job ({i+1}/{len(jobs_to_build)}): Job ULID: {job_data['job_ulid']} (ID: {job_data['id']})"
            )
            try:
                chapter_builder_service = ChapterBuilder(job_id=job_data["id"])
                chapter_builder_service.build_chapter_document()
                logger.info(
                    f"Successfully built chapter document for Job ULID: {job_data['job_ulid']}."
                )
            except Exception:
                logger.error(
                    f"Error building chapter document for Job ULID: {job_data['job_ulid']}.",
                    exc_info=True,
                )
            self.console.print()

        self.console.print("[green]Finished processing all eligible jobs.[/green]")
        logger.info("Finished bulk chapter building for all eligible jobs.")
        self.console.input("Press Enter to continue...")

    def _overwrite_chapter_document(self):
        """
        Prompts for a ULID and overwrites an existing chapter document if the job is eligible.
        """
        logger.info("Initiating overwrite chapter document process.")
        self.console.clear()
        self.console.rule("[bold blue]Overwrite Chapter Document[/bold blue]")

        ulid_input = Prompt.ask(
            "[bold yellow]Enter the Job ULID to overwrite (or 'b' to go back)[/bold yellow]"
        ).strip()
        logger.debug("User entered ULID for overwrite: '%s'", ulid_input)
        if ulid_input.lower() == "b":
            logger.info("User opted to go back from overwrite process.")
            return

        try:
            with get_session() as session:
                job_info = session.query(JobInfo).filter_by(job_ulid=ulid_input).first()

                if not job_info:
                    logger.warning(
                        f"Job with ULID '{ulid_input}' not found for overwrite."
                    )
                    self.console.print(
                        f"[red]Job with ULID '{ulid_input}' not found.[/red]"
                    )
                    self.console.input("Press Enter to continue...")
                    return

                metadata_stage = (
                    session.query(JobStage)
                    .filter_by(job_id=job_info.id, stage_name="extract_metadata")
                    .first()
                )
                edit_llm_stage = (
                    session.query(JobStage)
                    .filter_by(job_id=job_info.id, stage_name="edit_local_llm")
                    .first()
                )

                logger.debug(
                    f"Job {ulid_input}: Metadata stage state: {metadata_stage.state if metadata_stage else 'N/A'}"
                )
                logger.debug(
                    f"Job {ulid_input}: Edit LLM stage state: {edit_llm_stage.state if edit_llm_stage else 'N/A'}"
                )

                if not metadata_stage or metadata_stage.state != StageState.success:
                    logger.warning(
                        f"Job {ulid_input}: Metadata extraction stage is not successful. Cannot overwrite."
                    )
                    self.console.print(
                        f"[red]Job {ulid_input}: Metadata extraction stage is not successful. Cannot overwrite.[/red]"
                    )
                    self.console.input("Press Enter to continue...")
                    return

                if not edit_llm_stage or edit_llm_stage.state != StageState.success:
                    logger.warning(
                        f"Job {ulid_input}: Local LLM editing stage is not successful. Cannot overwrite."
                    )
                    self.console.print(
                        f"[red]Job {ulid_input}: Local LLM editing stage is not successful. Cannot overwrite.[/red]"
                    )
                    self.console.input("Press Enter to continue...")
                    return

                self.console.print(
                    f"[green]Job {ulid_input} is eligible for chapter overwrite.[/green]"
                )
                logger.info(f"Job {ulid_input} found eligible for overwrite.")
                confirm = Prompt.ask(
                    "[bold yellow]Confirm overwrite for this job? (y/n):[/bold yellow]"
                ).lower()
                logger.debug("User confirmation for overwrite: '%s'", confirm)

                if confirm == "y":
                    try:
                        chapter_builder_service = ChapterBuilder(job_id=job_info.id)
                        chapter_builder_service.build_chapter_document()
                        self.console.print(
                            f"[green]Chapter document for {ulid_input} overwritten.[/green]"
                        )
                        logger.info(
                            f"Chapter document for {ulid_input} successfully overwritten."
                        )
                    except Exception:
                        logger.error(
                            f"Error overwriting chapter document for Job ULID: {ulid_input}.",
                            exc_info=True,
                        )
                        self.console.print(
                            f"[red]Error overwriting chapter document for {ulid_input}. Check logs.[/red]"
                        )
                else:
                    self.console.print("[yellow]Overwrite cancelled.[/yellow]")
                    logger.info(
                        f"Overwrite for Job ULID {ulid_input} cancelled by user."
                    )

                self.console.input("Press Enter to continue...")
        except Exception:
            logger.error(
                f"An error occurred during the overwrite chapter document process for ULID '{ulid_input}'.",
                exc_info=True,
            )

    def run(self):
        """
        Main entry point for the chapter builder menu.
        """
        logger.info("Chapter Builder Menu started. Displaying menu.")
        while True:
            self.console.clear()
            self.console.rule("[bold blue]Chapter Builder Menu[/bold blue]")

            table = Table(
                title="Chapter Builder Options",
                show_header=True,
                header_style="bold magenta",
                box=config.BOX_STYLE,
                padding=(0, 2),
            )
            table.add_column("Option", style="cyan", width=8)
            table.add_column("Action", style="green")

            for key, val in self.options.items():
                table.add_row(key, val["desc"])

            self.console.print(table)

            choice = (
                Prompt.ask("[bold yellow]Select an option[/bold yellow]")
                .strip()
                .lower()
            )
            logger.debug("User selected menu option: '%s'", choice)

            selected_option = self.options.get(choice)

            if selected_option is None:
                logger.warning("Invalid choice in Chapter Builder Menu: '%s'", choice)
                self.console.print(
                    "[red]Invalid choice. Please select a valid option.[/red]"
                )
                self.console.input("Press Enter to continue...")
                continue

            action_func = selected_option.get("func")

            if action_func is None:
                logger.info("Exiting Chapter Builder Menu. User selected 'Back'.")
                break

            self.console.print(f"[cyan]Executing:[/cyan] {selected_option.get('desc')}")
            logger.info(
                "Executing Chapter Builder Menu action: '%s'",
                selected_option.get("desc"),
            )
            try:
                action_func()
            except Exception:
                logger.critical(
                    f"An unhandled error occurred while running '{selected_option.get('desc')}' in Chapter Builder Menu.",
                    exc_info=True,
                )
                self.console.print(
                    f"[bold red]An unexpected error occurred while running '{selected_option.get('desc')}'. Check logs for details.[/bold red]"
                )
                self.console.input("Press Enter to continue...")

        self.console.print("[bold green]Exiting Chapter Builder Menu.[/bold green]")
