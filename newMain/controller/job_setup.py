import logging
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from services import job_setup as job_setup_service
from config import config

logger = logging.getLogger(__name__)


class JobSetupController:
    """Controller for handling the job setup menu and user interactions."""

    def __init__(self):
        self.console = Console()
        self.options = {
            "1": {"desc": "Manual Entry", "func": self._handle_manual_entry},
            "2": {"desc": "CSV Entry", "func": self._handle_csv_entry},
            "b": {"desc": "Back to Main Menu", "func": None},
        }
        logger.debug("JobSetupController initialized with options: %s", self.options)

    def _handle_manual_entry(self):
        """Handles the logic for manual video URL entry."""
        logger.info("Starting manual entry flow.")
        self.console.print("[cyan]Starting manual entry flow...[/cyan]")

        try:
            # Instantiate and run the service class
            manual_job_setup = job_setup_service.ManualJobSetup()
            manual_job_setup.run()
            logger.info("Manual entry flow completed.")
        except Exception:
            logger.error("An error occurred during manual job setup.", exc_info=True)
            self.console.print(
                "[red]An error occurred during manual entry. Check logs.[/red]"
            )

        self.console.input("Press Enter to return to the Job Setup Menu...")

    def _handle_csv_entry(self):
        """Handles the logic for CSV file entry."""
        logger.info("Starting CSV entry flow.")
        self.console.print("[cyan]Starting CSV entry flow...[/cyan]")

        try:
            # Instantiate and run the service class
            csv_job_setup = job_setup_service.CsvJobSetup()
            csv_job_setup.run()
            logger.info("CSV entry flow completed.")
        except Exception:
            logger.error("An error occurred during CSV job setup.", exc_info=True)
            self.console.print(
                "[red]An error occurred during CSV entry. Check logs.[/red]"
            )

        self.console.input("Press Enter to return to the Job Setup Menu...")

    def run(self):
        """Displays the job setup menu and routes to the appropriate handler."""
        logger.info("Job Setup Menu started. Displaying menu.")
        while True:
            console = self.console

            console.clear()
            console.rule("[bold blue]Job Setup Menu[/bold blue]")

            table = Table(
                title="Job Setup Options",
                show_header=True,
                header_style="bold magenta",
                box=config.BOX_STYLE,
                padding=(0, 2),
            )
            table.add_column("Option", style="cyan", width=8)
            table.add_column("Action", style="green")

            for key, val in self.options.items():
                table.add_row(key, val["desc"])

            console.print(table)
            choice = Prompt.ask("[bold yellow]Select an option[/bold yellow]").strip()
            logger.debug("User selected menu option: '%s'", choice)
            selected_option = self.options.get(choice)

            if selected_option is None:
                logger.warning("Invalid choice in Job Setup Menu: '%s'", choice)
                console.print(
                    "[red]Invalid choice. Please select a valid option.[/red]"
                )
                console.input("Press Enter to continue...")
                continue

            action_func = selected_option.get("func")

            if action_func is None:
                # This is the 'Back' option
                logger.info("Exiting Job Setup Menu. User selected 'Back'.")
                break

            logger.info("Executing Job Setup action: '%s'", selected_option.get("desc"))
            try:
                action_func()
            except Exception:
                logger.critical(
                    f"An unhandled error occurred while running '{selected_option.get('desc')}' in Job Setup Menu.",
                    exc_info=True,
                )
                self.console.print(
                    f"[bold red]An unexpected error occurred while running '{selected_option.get('desc')}'. Check logs for details.[/bold red]"
                )
                self.console.input("Press Enter to continue...")
