from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from services import whisper_deployer
from config import config


class Menu:
    def __init__(self):
        self.console = Console()
        self.options = {
            '1': {'desc': 'Deploy Pending Jobs', 'func': self._deploy},
            '2': {'desc': 'Check For Completed Jobs', 'func': self._recover},
            '3': {'desc': 'Manually Retrieve Job', 'func': self._manually_recover},
            'b': {'desc': 'Back to Main Menu', 'func': None}
        }

        self.deployer = whisper_deployer.Deployer()
    
    def run(self):
        console = self.console
        while True:
            console.clear()
            self._display_menu()
            choice = Prompt.ask("[bold green]Enter your choice[/bold green]", choices=list(self.options.keys())).lower()

            if choice == 'b':
                break
            
            action = self.options.get(choice)
            if action and action['func']:
                action['func']()
            else:
                console.print("[bold red]Invalid choice. Please try again.[/bold red]")
            
            Prompt.ask("Press Enter to continue...")
    
    def _display_menu(self):
        self.console.print("[bold cyan]Whisper Deployment Menu[/bold cyan]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Option", style="dim", width=12)
        table.add_column("Description")

        for key, value in self.options.items():
            table.add_row(key, value['desc'])
        
        self.console.print(table)
    
    def _deploy(self):
        self.deployer.deploy_pending_jobs()

    def _recover(self):
        self.deployer.check_for_completed_jobs()

    def _manually_recover(self):
        job_id = Prompt.ask("[bold green]Enter the Job ID to retrieve[/bold green]")
        if job_id:
            self.deployer.recover_specific_job(job_id)
