from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich import box

from controller import job_setup
from config import config

def main():
    """
    Top-level CLI menu for the sermon pipeline program, using Rich for visuals.
    """
    console = Console()
    options = {
        '1': {'desc': 'Job Setup Menu', 'func': job_setup.job_setup_menu},
        'q': {'desc': 'Exit', 'func': None}
    }

    while True:
        console.clear()
        console.rule("[bold blue]Sermon Pipeline Main Menu[/bold blue]")

        table = Table(
            title="Available Options",
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

        # Get the selected option dictionary safely
        selected_option = options.get(choice)

        if selected_option is None:
            console.print("[red]Invalid choice. Please select a valid option.[/red]")
            console.input("Press Enter to continue...")
            continue  # go back to menu

        # Get the function assigned to this option
        action_func = selected_option.get('func')

        if action_func is None:
            console.print("[bold red]Goodbye![/bold red]")
            break  # exit the loop

        # Execute the function
        console.print(f"[cyan]Executing:[/cyan] {selected_option.get('desc')}")
        action_func()
        #break
