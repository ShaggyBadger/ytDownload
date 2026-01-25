from rich.console import Console
from rich.table import Table

from database.session_manager import get_session
from database.models import JobInfo, JobStage, StageState, STAGE_ORDER
from services.metadata_extractor import GenerateMetadata

console = Console()

def _get_run_all_jobs():
    """
    Retrieves jobs where 'format_gemini' is successful, and 'extract_metadata' is pending or failed.
    """
    with get_session() as session:        # Subquery to find jobs where format_gemini is successful
        successful_format_gemini_jobs = session.query(JobStage.job_id).filter(
            JobStage.stage_name == "format_gemini",
            JobStage.state == StageState.success
        ).subquery()

        # Query for jobs that are in the successful_format_gemini_jobs list
        # AND where extract_metadata is pending or failed
        runnable_jobs_query = session.query(
            JobInfo.id,
            JobInfo.job_ulid,
            JobInfo.video_id,
            JobInfo.job_directory
        ).join(JobStage).filter(
            JobInfo.id == successful_format_gemini_jobs.c.job_id,
            JobStage.stage_name == "extract_metadata",
            JobStage.state.in_([StageState.pending, StageState.failed])
        ).distinct()

        return [{"id": job.id, "job_ulid": job.job_ulid, "video_id": job.video_id, "job_directory": job.job_directory} for job in runnable_jobs_query.all()]

def _get_manual_selection_jobs():
    """
    Retrieves jobs where 'format_gemini' stage is successful.
    """
    with get_session() as session:        # Subquery to find jobs where format_gemini is successful
        successful_format_gemini_jobs = session.query(JobStage.job_id).filter(
            JobStage.stage_name == "format_gemini",
            JobStage.state == StageState.success
        ).subquery()

        # Query for JobInfo objects that match these job_ids
        jobs_for_manual_selection = session.query(
            JobInfo.id,
            JobInfo.job_ulid,
            JobInfo.video_id,
            JobInfo.job_directory
        ).filter(
            JobInfo.id == successful_format_gemini_jobs.c.job_id
        ).all()
        return [{"id": job.id, "job_ulid": job.job_ulid, "video_id": job.video_id, "job_directory": job.job_directory} for job in jobs_for_manual_selection]

def _display_jobs(jobs, title="Available Jobs"):
    """
    Displays a list of jobs in a formatted table.
    """
    if not jobs:
        console.print(f"[bold yellow]No {title.lower()} found.[/bold yellow]")
        return

    table = Table(title=title)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("ULID", style="magenta")
    table.add_column("Video ID", style="green")
    table.add_column("Job Directory", style="blue")

    for job in jobs:
        table.add_row(
            str(job['id']),
            job['job_ulid'],
            str(job['video_id']),
            job['job_directory']
        )
    console.print(table)

def _run_metadata_extraction(job_ids: list[int]):
    """
    Iterates through job IDs and triggers the metadata extraction service.
    """
    if not job_ids:
        console.print("[bold yellow]No jobs selected for metadata extraction.[/bold yellow]")
        return

    for job_id in job_ids:
        with console.status(f"[bold green]Processing metadata for Job ID: {job_id}...[/bold green]", spinner="dots"):
            extractor = GenerateMetadata(job_id=job_id, console=console) # Pass console
            extractor.process_job()
        console.print(f"[bold green]Finished processing metadata for Job ID: {job_id}.[/bold green]\n")

def metadata_generator_menu():
    """
    Provides a menu for managing metadata generation tasks.
    """
    while True:
        console.clear()
        console.print("\n[bold]Metadata Generator Menu[/bold]")
        console.print("1. Run All eligible jobs")
        console.print("2. Select jobs manually")
        console.print("0. Back to Main Menu")

        choice = console.input("[bold]Enter your choice:[/bold] ")

        if choice == '1':
            console.print("[bold blue]Fetching eligible jobs for 'Run All' ...[/bold blue]")
            jobs_to_run = _get_run_all_jobs()
            _display_jobs(jobs_to_run, title="Eligible Jobs for Automatic Metadata Extraction")
            if jobs_to_run:
                confirm = console.input("[bold yellow]Confirm running metadata extraction for these jobs? (y/n):[/bold yellow] ").lower()
                if confirm == 'y':
                    _run_metadata_extraction([job['id'] for job in jobs_to_run])
                else:
                    console.print("[bold red]Metadata extraction cancelled.[/bold red]")

        elif choice == '2':
            console.print("[bold blue]Fetching jobs for manual selection...[/bold blue]")
            jobs_for_selection = _get_manual_selection_jobs()
            _display_jobs(jobs_for_selection, title="Jobs with Successful Formatted Transcripts")

            if jobs_for_selection:
                while True:
                    selected_ids_input = console.input("[bold]Enter Job IDs to process (comma-separated), or 'b' to go back:[/bold] ")
                    if selected_ids_input.lower() == 'b':
                        break
                    try:
                        selected_ids = [int(x.strip()) for x in selected_ids_input.split(',') if x.strip()]
                        valid_selected_ids = [job_id for job_id in selected_ids if job_id in [job['id'] for job in jobs_for_selection]]
                        if valid_selected_ids:
                            _run_metadata_extraction(valid_selected_ids)
                            break
                        else:
                            console.print("[bold red]No valid Job IDs entered or selected IDs are not in the list. Please try again.[/bold red]")
                    except ValueError:
                        console.print("[bold red]Invalid input. Please enter comma-separated numbers.[/bold red]")
            else:
                console.print("[bold yellow]No jobs available for manual selection.[/bold yellow]")

        elif choice == '0':
            break
        else:
            console.print("[bold red]Invalid choice. Please try again.[/bold red]")
