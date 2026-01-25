from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from controller import job_setup
from controller import job_download
from controller import whisper_deploy_menu
from controller import format_transcription
from config import config

class MainMenuController:
    """
    Top-level CLI menu for the sermon pipeline program, using Rich for visuals.
    Encapsulates the main menu logic and handles user interaction to navigate
    to different parts of the application.
    """

    def __init__(self):
        self.console = Console()
        self.options = {
            '1': {'desc': 'Job Setup Menu', 'func': self._run_job_setup_menu},
            '2': {'desc': 'Download and Trim Jobs', 'func': self._run_job_download_menu},
            '3': {'desc': 'Deploy/Retrieve Jobs to Server', 'func': self._run_whisper_deployment},
            '4': {'desc': 'Format Textblocks', 'func': self._run_formatter},
            'q': {'desc': 'Exit', 'func': None}
        }

    def _run_job_setup_menu(self):
        """Instantiates and runs the job setup controller."""
        setup_controller = job_setup.JobSetupController()
        setup_controller.run()
    
    def _run_job_download_menu(self):
        """Instantiates and runs the job download controller"""
        download_controller = job_download.JobDownloadController()
        download_controller.run()

    def _run_whisper_deployment(self):
        """Activates script to deploy jobs to the server for transcription"""
        deployment_controller = whisper_deploy_menu.Menu()
        deployment_controller.run()

    def _run_formatter(self):
        """Activates script to format whisperAI slop into nice paragraphs"""
        format_controller = format_transcription.FormatTranscriptionController()
        format_controller.run()

    def run(self):
        """
        Displays the main menu and handles user choices.
        """
        while True:
            console = self.console
            
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
                console.print("[bold red]Goodbye![/bold red]")
                break

            console.print(f"[cyan]Executing:[/cyan] {selected_option.get('desc')}")
            action_func()
        #break
