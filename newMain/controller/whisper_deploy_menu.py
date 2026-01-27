import logging
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from services import whisper_deployer
from config import config

logger = logging.getLogger(__name__)

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
        logger.debug("Whisper Deploy Menu initialized with options: %s", self.options)
        logger.debug("whisper_deployer.Deployer instance created.")
    
    def run(self):
        logger.info("Whisper Deploy Menu started. Displaying menu.")
        console = self.console
        while True:
            console.clear()
            self._display_menu()
            choice = Prompt.ask("[bold green]Enter your choice[/bold green]", choices=list(self.options.keys())).lower()
            logger.debug("User selected menu option: '%s'", choice)

            if choice == 'b':
                logger.info("Exiting Whisper Deploy Menu. User selected 'Back'.")
                break
            
            action = self.options.get(choice)
            if action and action['func']:
                logger.info("Executing Whisper Deploy action: '%s'", action.get('desc'))
                try:
                    action['func']()
                except Exception:
                    logger.critical(f"An unhandled error occurred while running '{action.get('desc')}' in Whisper Deploy Menu.", exc_info=True)
                    self.console.print(f"[bold red]An unexpected error occurred while running '{action.get('desc')}'. Check logs for details.[/bold red]")
                    self.console.input("Press Enter to continue...")
            else:
                logger.warning("Invalid choice in Whisper Deploy Menu: '%s'", choice)
                console.print("[bold red]Invalid choice. Please try again.[/bold red]")
            
            Prompt.ask("Press Enter to continue...")
        logger.info("Exited Whisper Deploy Menu.")
    
    def _display_menu(self):
        logger.debug("Displaying Whisper Deployment Menu options.")
        self.console.print("[bold cyan]Whisper Deployment Menu[/bold cyan]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Option", style="dim", width=12)
        table.add_column("Description")

        for key, value in self.options.items():
            table.add_row(key, value['desc'])
        
        self.console.print(table)
    
    def _deploy(self):
        logger.info("Calling deploy_pending_jobs from whisper_deployer.")
        try:
            self.deployer.deploy_pending_jobs()
            logger.info("deploy_pending_jobs completed.")
        except Exception:
            logger.error("Error deploying pending jobs.", exc_info=True)
            self.console.print("[red]An error occurred during deployment. Check logs for details.[/red]")

    def _recover(self):
        logger.info("Calling check_for_completed_jobs from whisper_deployer.")
        try:
            self.deployer.check_for_completed_jobs()
            logger.info("check_for_completed_jobs completed.")
        except Exception:
            logger.error("Error checking for completed jobs.", exc_info=True)
            self.console.print("[red]An error occurred during job status check. Check logs for details.[/red]")

    def _manually_recover(self):
        logger.info("Initiating manual job recovery.")
        job_id = Prompt.ask("[bold green]Enter the Job ID to retrieve[/bold green]")
        logger.debug("User entered Job ID for manual recovery: '%s'", job_id)
        if job_id:
            try:
                self.deployer.recover_specific_job(job_id)
                logger.info(f"Manual recovery initiated for Job ID: {job_id}.")
            except Exception:
                logger.error(f"Error during manual recovery for Job ID: {job_id}.", exc_info=True)
                self.console.print(f"[red]An error occurred during manual recovery for Job ID {job_id}. Check logs for details.[/red]")
        else:
            logger.warning("No Job ID provided for manual recovery.")
            self.console.print("[yellow]No Job ID provided for manual recovery.[/yellow]")