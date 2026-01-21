from rich.console import Console

from .menu import Menu
from .csv_links import CSVLinksProcessor
from .manual_link import ManualLinkProcessor

class Processor():
    def __init__(self):
        self.console = Console()
        self.menu = Menu(self.console)
        self.csv_processor = CSVLinksProcessor()
        self.manual_processor = ManualLinkProcessor()

        # Define the action map
        self._actions = {
            'csv_links': self.csv_processor.process_links,
            'manual_link': self.manual_processor.process_link,
            'back': self.back_to_main
        }

    def run(self):
        action = self.menu.run()

        if action in self._actions:
            # Call the corresponding method
            if action == 'back':
                return self._actions[action]()
            
            self._actions.get(action)()
            return True # Continue loop for other actions
        
        else:
            self.console.print(f"[bold red]Error: Unknown action '{action}'.[/bold red]")
            return True # Continue loop for unknown actions
    
    def back_to_main(self):
        self.console.print("[bold green]Returning to Main Menu...[/bold green]")
        return None
