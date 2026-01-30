import logging
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from pathlib import Path
import json

from database.session_manager import get_session
from database.models import JobInfo, JobStage, StageState
from services.metadata_extractor import MetadataExtractor
from config import config

logger = logging.getLogger(__name__)
console = Console()  # Console for user interaction messages


def _get_jobs_for_metadata_processing():
    """
    Retrieves jobs where 'format_gemini' is successful and the metadata.json file
    is either missing or has null categories.
    """
    logger.debug("Querying for jobs eligible for metadata processing.")
    eligible_jobs = []
    try:
        with get_session() as session:
            successful_format_gemini_jobs = (
                session.query(JobStage.job_id)
                .filter(
                    JobStage.stage_name == "format_gemini",
                    JobStage.state == StageState.success,
                )
                .subquery()
            )
            logger.debug("Subquery for successful 'format_gemini' jobs executed.")

            candidate_jobs_query = (
                session.query(
                    JobInfo.id.label("job_id"),
                    JobInfo.job_ulid.label("job_ulid"),
                    JobInfo.job_directory.label("job_directory"),
                    JobStage.state.label("metadata_stage_state"),
                )
                .join(JobStage, JobInfo.id == JobStage.job_id)
                .filter(
                    JobInfo.id == successful_format_gemini_jobs.c.job_id,
                    JobStage.stage_name == "extract_metadata",
                )
                .distinct()
                .all()
            )
            logger.debug(
                f"Found {len(candidate_jobs_query)} candidate jobs for metadata processing."
            )

            for job_data in candidate_jobs_query:
                job_directory = Path(job_data.job_directory)
                metadata_path = job_directory / config.METADATA_FILE_NAME

                needs_processing = False

                if not metadata_path.exists():
                    logger.info(
                        f"Metadata file not found at {metadata_path} for job {job_data.job_ulid}. Marking as eligible."
                    )
                    needs_processing = True
                else:
                    try:
                        with open(metadata_path, "r") as f:
                            metadata = json.load(f)

                        for category in config.METADATA_CATEGORIES:
                            if metadata.get(category) is None:
                                logger.debug(
                                    f"Job {job_data.job_ulid} metadata '{category}' is null. Marking as eligible."
                                )
                                needs_processing = True
                                break
                    except json.JSONDecodeError:
                        logger.error(
                            f"Corrupt metadata.json for job {job_data.job_ulid} at {metadata_path}. Marking as eligible.",
                            exc_info=True,
                        )
                        console.print(
                            f"[red]Warning: Corrupt metadata.json for job {job_data.job_ulid} at {metadata_path}. Marking as eligible.[/red]"
                        )
                        needs_processing = True
                    except Exception:
                        logger.error(
                            f"Error checking metadata.json for job {job_data.job_ulid} at {metadata_path}.",
                            exc_info=True,
                        )
                        console.print(
                            f"[red]Error reading metadata.json for job {job_data.job_ulid} at {metadata_path}. Marking as eligible.[/red]"
                        )
                        needs_processing = True

                if needs_processing:
                    eligible_jobs.append(
                        {
                            "id": job_data.job_id,
                            "job_ulid": job_data.job_ulid,
                            "job_directory": job_data.job_directory,
                            "metadata_stage_state": job_data.metadata_stage_state.value,
                        }
                    )
        logger.info(
            f"Identified {len(eligible_jobs)} jobs eligible for metadata processing."
        )
    except Exception:
        logger.error(
            "Error querying for jobs eligible for metadata processing.", exc_info=True
        )
    return eligible_jobs


def _display_jobs(jobs, title="Available Jobs"):
    """
    Displays a list of jobs in a formatted table.
    """
    logger.debug(f"Displaying jobs table for: '{title}'. Number of jobs: {len(jobs)}")
    if not jobs:
        logger.info(f"No jobs to display for '{title}'.")
        console.print(f"[bold yellow]No {title.lower()} found.[/bold yellow]")
        return

    table = Table(title=title)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("ULID", style="magenta")
    table.add_column("Job Directory", style="blue")
    table.add_column("Metadata Status", style="yellow")

    for job in jobs:
        table.add_row(
            str(job["id"]),
            job["job_ulid"],
            job["job_directory"],
            job["metadata_stage_state"],
        )
    console.print(table)


def _run_metadata_processing(job_ids: list[int]):
    """
    Iterates through job IDs and triggers the metadata processing service.
    """
    logger.info(f"Running metadata processing for job IDs: {job_ids}")
    if not job_ids:
        logger.warning("No job IDs provided for metadata processing.")
        console.print(
            "[bold yellow]No jobs selected for metadata processing.[/bold yellow]"
        )
        return

    for job_id in job_ids:
        logger.info(f"Processing metadata for Job ID: {job_id}.")
        try:
            extractor = MetadataExtractor(job_id=job_id)
            extractor.process_metadata()
            logger.info(
                f"Successfully finished processing metadata for Job ID: {job_id}."
            )
            console.print(
                f"[bold green]Finished processing metadata for Job ID: {job_id}.[/bold green]\n"
            )
        except Exception:
            logger.error(
                f"Error processing metadata for Job ID: {job_id}.", exc_info=True
            )
            console.print(
                f"[bold red]Error processing metadata for Job ID: {job_id}. Check logs.[/bold red]\n"
            )


def metadata_generator_menu():
    """
    Provides a menu for managing metadata generation tasks.
    """
    logger.info("Metadata Generator Menu started. Displaying menu.")
    while True:
        console.clear()
        console.print("\n[bold]Metadata Generator Menu[/bold]")
        console.print("1. Process all eligible jobs")
        console.print("2. Select jobs manually")
        console.print("0. Back to Main Menu")

        choice = Prompt.ask("[bold]Enter your choice:[/bold] ")
        logger.debug("User selected menu option: '%s'", choice)

        if choice == "1":
            logger.info("User selected 'Process all eligible jobs'.")
            console.print(
                "[bold blue]Fetching eligible jobs for processing...[/bold blue]"
            )
            jobs_to_run = _get_jobs_for_metadata_processing()
            _display_jobs(
                jobs_to_run, title="Eligible Jobs for Automatic Metadata Processing"
            )
            if jobs_to_run:
                confirm = Prompt.ask(
                    "[bold yellow]Confirm processing metadata for these jobs? (y/n):[/bold yellow] "
                ).lower()
                logger.debug(
                    "User confirmation for processing all eligible jobs: '%s'", confirm
                )
                if confirm == "y":
                    _run_metadata_processing([job["id"] for job in jobs_to_run])
                else:
                    logger.info(
                        "Metadata processing for all eligible jobs cancelled by user."
                    )
                    console.print("[bold red]Metadata processing cancelled.[/bold red]")

        elif choice == "2":
            logger.info("User selected 'Select jobs manually'.")
            console.print(
                "[bold blue]Fetching jobs for manual selection...[/bold blue]"
            )
            jobs_for_selection = (
                _get_jobs_for_metadata_processing()
            )  # Use the same method for eligibility
            _display_jobs(jobs_for_selection, title="Jobs with Metadata to Process")

            if jobs_for_selection:
                while True:
                    selected_ids_input = Prompt.ask(
                        "[bold]Enter Job IDs to process (comma-separated), or 'b' to go back:[/bold] "
                    )
                    logger.debug(
                        "User entered selected IDs for manual processing: '%s'",
                        selected_ids_input,
                    )
                    if selected_ids_input.lower() == "b":
                        logger.info("User opted to go back from manual selection.")
                        break
                    try:
                        selected_ids = [
                            int(x.strip())
                            for x in selected_ids_input.split(",")
                            if x.strip()
                        ]
                        valid_selected_ids = [
                            job_id
                            for job_id in selected_ids
                            if job_id in [job["id"] for job in jobs_for_selection]
                        ]
                        logger.debug("Valid selected Job IDs: %s", valid_selected_ids)
                        if valid_selected_ids:
                            _run_metadata_processing(valid_selected_ids)
                            break
                        else:
                            logger.warning(
                                "No valid Job IDs entered or selected IDs are not in the list: %s",
                                selected_ids_input,
                            )
                            console.print(
                                "[bold red]No valid Job IDs entered or selected IDs are not in the list. Please try again.[/bold red]"
                            )
                    except ValueError:
                        logger.error(
                            "Invalid input for Job IDs (not comma-separated numbers): '%s'",
                            selected_ids_input,
                            exc_info=True,
                        )
                        console.print(
                            "[bold red]Invalid input. Please enter comma-separated numbers.[/bold red]"
                        )
            else:
                logger.info("No jobs available for manual selection.")
                console.print(
                    "[bold yellow]No jobs available for manual selection.[/bold yellow]"
                )

        elif choice == "0":
            logger.info(
                "Exiting Metadata Generator Menu. User selected 'Back to Main Menu'."
            )
            break
        else:
            logger.warning("Invalid choice in Metadata Generator Menu: '%s'", choice)
            console.print("[bold red]Invalid choice. Please try again.[/bold red]")
