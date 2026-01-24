from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from services import job_download_service
from config import config

class JobDownloadController:
    """Controller for handling the job setup menu and user interactions."""

    def __init__(self):
        self.console = Console()
        self.options = {
            '1': {'desc': 'Download All Jobs', 'func': self._download_all},
            '2': {'desc': 'Select Job to Download', 'func': self._select_download},
            'b': {'desc': 'Back to Main Menu', 'func': None}
        }

    def _download_all(self):
        controller = job_download_service.Downloader()
        controller.run_all()

    def _select_download(self):
        pass

    def run(self):
        """Displays the job download menu and routes to the appropriate handler."""
        while True:
            console = self.console

            console.clear()
            console.rule("[bold blue]Job Download Menu[/bold blue]")

            table = Table(
                title="Job Download Options",
                show_header=True,
                header_style="bold magenta",
                box=config.BOX_STYLE,
                padding=(0,2) # top/bottom, left/right
                )
            table.add_column("Option", style="cyan", width=8)
            table.add_column("Action", style="green")

            for key, val in self.options.items():
                table.add_row(key, val['desc'])

            console.print(table)
            choice = Prompt.ask("[bold yellow]Select an option[/bold yellow]").strip()
            selected_option = self.options.get(choice)

            if selected_option is None:
                console.print("[red]Invalid choice. Please select a valid option.[/red]")
                console.input("Press Enter to continue...")
                continue

            action_func = selected_option.get('func')

            if action_func is None:
                # This is the 'Back' option
                break

            # Execute the selected job setup function
            action_func()
