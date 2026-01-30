import logging
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from pathlib import Path

from sqlalchemy.orm import joinedload

from services.evaluator import Evaluator, EvaluatorInitialization
from config import config
from database.session_manager import get_session
from database.models import JobInfo, VideoInfo

logger = logging.getLogger(__name__)


class EvaluatorMenu:
    def __init__(self):
        self.console = Console()
        self.options = {
            "1": {
                "desc": "Run evaluation for a single job",
                "func": self._select_and_evaluate_single_job,
            },
            "2": {
                "desc": "Run evaluation for ALL jobs",
                "func": self._evaluate_all_jobs,
            },
            "b": {"desc": "Back to Main Menu", "func": None},
        }
        logger.debug("EvaluatorMenu initialized.")

    def run(self):
        """Main entry point for the evaluator menu."""
        logger.info("Evaluator Menu started.")

        with self.console.status(
            "Initializing evaluation settings for all jobs...", spinner=config.SPINNER
        ):
            try:
                all_jobs = self._get_all_jobs_from_db()
                initializer = EvaluatorInitialization()
                for job_data in all_jobs:
                    job_dir = Path(job_data["job_directory"])
                    logger.debug(f"Auto-initializing {job_dir.name}")
                    initializer.run_initialization(job_dir)
                logger.info("Automatic initialization complete for all jobs.")
            except Exception as e:
                logger.error(f"Automatic initialization failed: {e}", exc_info=True)
                self.console.print(
                    "[bold red]Automatic initialization failed. Check logs.[/bold red]"
                )

        while True:
            self.console.clear()
            self.console.rule("[bold blue]Evaluator Menu[/bold blue]")
            self._display_menu()
            choice = (
                Prompt.ask("[bold yellow]Select an option[/bold yellow]")
                .strip()
                .lower()
            )
            logger.debug(f"User selected option: '{choice}'")

            selected_option = self.options.get(choice)
            if not selected_option:
                self.console.print(
                    "[red]Invalid choice. Please select a valid option.[/red]"
                )
                self.console.input("Press Enter to continue...")
                continue

            action_func = selected_option.get("func")
            if action_func is None:
                logger.info("Exiting Evaluator Menu.")
                break

            self.console.print(f"[cyan]Executing:[/cyan] {selected_option['desc']}")
            try:
                action_func()
            except Exception as e:
                logger.critical(
                    f"An unhandled error occurred while running '{selected_option['desc']}'. Error: {e}",
                    exc_info=True,
                )
                self.console.print(
                    f"[bold red]An unexpected error occurred. Check logs for details.[/bold red]"
                )

            self.console.input("Press Enter to continue...")

    def _display_menu(self):
        """Displays the main menu table."""
        table = Table(
            title="Evaluation Options",
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

    def _get_all_jobs_from_db(self) -> list[dict]:
        """Queries the database for all jobs with an existing job directory."""
        logger.debug("Querying database for all jobs.")
        jobs_list = []
        try:
            with get_session() as session:
                jobs = (
                    session.query(JobInfo)
                    .options(joinedload(JobInfo.video))
                    .order_by(JobInfo.id)
                    .all()
                )
                for job in jobs:
                    if job.job_directory and Path(job.job_directory).exists():
                        jobs_list.append(
                            {
                                "id": job.id,
                                "job_ulid": job.job_ulid,
                                "title": job.video.title if job.video else "N/A",
                                "job_directory": job.job_directory,
                            }
                        )
                    else:
                        logger.warning(
                            f"Job {job.job_ulid} has no directory or path does not exist. Skipping."
                        )
            logger.info(
                f"Found {len(jobs_list)} jobs in the database with existing directories."
            )
            return jobs_list
        except Exception as e:
            logger.error(f"Error querying jobs from database: {e}", exc_info=True)
            self.console.print("[bold red]Error accessing database.[/bold red]")
            return []

    def _select_job(self) -> dict | None:
        """Displays a list of jobs from DB and prompts user to select one."""
        self.console.rule("[bold blue]Select a Job[/bold blue]")
        jobs = self._get_all_jobs_from_db()
        if not jobs:
            self.console.print("[yellow]No jobs found in the database.[/yellow]")
            return None

        table = Table(
            show_header=True, header_style="bold magenta", box=config.BOX_STYLE
        )
        table.add_column("No.", style="cyan", width=5)
        table.add_column("Job ULID", style="green")
        table.add_column("Title", style="green")

        job_map = {}
        for i, job_data in enumerate(jobs):
            display_num = str(i + 1)
            job_map[display_num] = job_data
            table.add_row(display_num, job_data["job_ulid"], job_data["title"])

        self.console.print(table)

        while True:
            choice = (
                Prompt.ask(
                    "[bold yellow]Select a job by number (or 'b' to go back)[/bold yellow]"
                )
                .strip()
                .lower()
            )
            if choice == "b":
                return None

            selected_job = job_map.get(choice)
            if selected_job:
                return selected_job
            else:
                self.console.print("[red]Invalid selection.[/red]")

    def _select_and_evaluate_single_job(self):
        """Handler for evaluating a single job."""
        self.console.rule("[bold blue]Evaluate Single Job[/bold blue]")
        job_data = self._select_job()
        if job_data:
            job_dir = Path(job_data["job_directory"])
            self.console.print(f"Evaluating job: [cyan]{job_dir.name}[/cyan]")
            evaluator = Evaluator()
            evaluator.run_evaluation(job_dir)
            self.console.print("[green]Evaluation complete.[/green]")

    def _evaluate_all_jobs(self):
        """Handler for evaluating all jobs."""
        self.console.rule("[bold blue]Evaluate All Jobs[/bold blue]")
        all_jobs = self._get_all_jobs_from_db()
        if not all_jobs:
            self.console.print("[yellow]No jobs to evaluate.[/yellow]")
            return

        total = len(all_jobs)
        self.console.print(f"Found {total} jobs to evaluate.")
        evaluator = Evaluator()
        for i, job_data in enumerate(all_jobs, 1):
            job_dir = Path(job_data["job_directory"])
            self.console.print(
                f"({i}/{total}) Evaluating job: [cyan]{job_dir.name}[/cyan]"
            )
            evaluator.run_evaluation(job_dir)
        self.console.print("[green]All jobs evaluated.[/green]")
