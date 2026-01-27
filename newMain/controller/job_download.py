import logging
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from services import job_download_service
from config import config

logger = logging.getLogger(__name__)

class JobDownloadController:
    """Controller for handling the job download menu and user interactions."""

    def __init__(self):
        self.console = Console()
        self.options = {
            '1': {'desc': 'Download All Jobs', 'func': self._download_all},
            '2': {'desc': 'Select Job to Download', 'func': self._select_download},
            'b': {'desc': 'Back to Main Menu', 'func': None}
        }
        logger.debug("JobDownloadController initialized with options: %s", self.options)

    def _download_all(self):
        logger.info("Handling 'Download All Jobs' action.")
        try:
            controller = job_download_service.Downloader()
            controller.run_all()
            logger.info("'Download All Jobs' action completed.")
        except Exception:
            logger.error("An error occurred during 'Download All Jobs' action.", exc_info=True)
            self.console.print("[red]An error occurred during 'Download All Jobs'. Check logs for details.[/red]")

    def _select_download(self):
        logger.info("Handling 'Select Job to Download' action.")
        try:
            controller = job_download_service.Downloader()
            controller.run_one()
            logger.info("'Select Job to Download' action completed.")
        except Exception:
            logger.error("An error occurred during 'Select Job to Download' action.", exc_info=True)
            self.console.print("[red]An error occurred during 'Select Job to Download'. Check logs for details.[/red]")

    def run(self):
        """Displays the job download menu and routes to the appropriate handler."""
        logger.info("Job Download Menu started. Displaying menu.")
        while True:
            console = self.console

            console.clear()
            console.rule("[bold blue]Job Download Menu[/bold blue]")

            table = Table(
                title="Job Download Options",
                show_header=True,
                header_style="bold magenta",
                box=config.BOX_STYLE,
                padding=(0,2)
                )
            table.add_column("Option", style="cyan", width=8)
            table.add_column("Action", style="green")

            for key, val in self.options.items():
                table.add_row(key, val['desc'])

            console.print(table)
            choice = Prompt.ask("[bold yellow]Select an option[/bold yellow]").strip()
            logger.debug("User selected menu option: '%s'", choice)
            selected_option = self.options.get(choice)

            if selected_option is None:
                logger.warning("Invalid choice in Job Download Menu: '%s'", choice)
                console.print("[red]Invalid choice. Please select a valid option.[/red]")
                console.input("Press Enter to continue...")
                continue

            action_func = selected_option.get('func')

            if action_func is None:
                # This is the 'Back' option
                logger.info("Exiting Job Download Menu. User selected 'Back'.")
                break

            logger.info("Executing Job Download action: '%s'", selected_option.get('desc'))
            try:
                action_func()
            except Exception:
                logger.critical(f"An unhandled error occurred while running '{selected_option.get('desc')}' in Job Download Menu.", exc_info=True)
                self.console.print(f"[bold red]An unexpected error occurred while running '{selected_option.get('desc')}'. Check logs for details.[/bold red]")
                self.console.input("Press Enter to continue...")