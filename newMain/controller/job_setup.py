from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich import box
import random # This import is not used. Removing it.

from services import job_setup as job_setup_service
from config import config

def _handle_manual_entry():
    """Handles the logic for manual video URL entry."""
    console = Console()
    console.print("[cyan]Starting manual entry flow...[/cyan]")
    
    # Instantiate and run the service class
    manual_job_setup = job_setup_service.ManualJobSetup()
    manual_job_setup.run()
    
    console.input("Press Enter to return to the Job Setup Menu...")

def _handle_csv_entry():
    """Handles the logic for CSV file entry."""
    console = Console()
    console.print("[cyan]Starting CSV entry flow...[/cyan]")

    # Instantiate and run the service class
    csv_job_setup = job_setup_service.CsvJobSetup()
    csv_job_setup.run()

    console.input("Press Enter to return to the Job Setup Menu...")

def job_setup_menu():
    """Displays the job setup menu and routes to the appropriate handler."""
    console = Console()
    
    options = {
        '1': {'desc': 'Manual Entry', 'func': _handle_manual_entry},
        '2': {'desc': 'CSV Entry', 'func': _handle_csv_entry},
        'b': {'desc': 'Back to Main Menu', 'func': None}
    }

    while True:
        console.clear()
        console.rule("[bold blue]Job Setup Menu[/bold blue]")

        table = Table(
            title="Job Setup Options",
            show_header=True,
            header_style="bold magenta",
            box=config.BOX_STYLE,
            padding=(0,2) # top/bottom, left/right
            )
        table.add_column("Option", style="cyan", width=8)
        table.add_column("Action", style="green")

        for key, val in options.items():
            table.add_row(key, val['desc'])

        console.print(table)

        choice = Prompt.ask("[bold yellow]Select an option[/bold yellow]").strip()

        selected_option = options.get(choice)

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
