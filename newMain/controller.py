from rich.console import Console

from config import Config
from downloader import Downloader
from process_new_links import Processor
from menus import MainMenu

class Controller():
    def __init__(self):
        self.console = Console()

        self.config = Config()
        self.downloader = Downloader()
        self.processor = Processor()
        self.main_menu = MainMenu(self.console)

        # Define the action map
        self._actions = {
            'process_links': self.processor.run,
            'download_videos': self.downloader.run,
            'quit': self._quit_application
        }
    
    def _quit_application(self):
        self.console.print("[bold green]Exiting application. Goodbye![/bold green]")
        return False # Signal to stop the loop

    def run_action(self, action):
        if action in self._actions:
            # Call the corresponding method
            # For quit, we return the boolean to signal the loop to stop
            if action == 'quit':
                return self._actions[action]()
            else:
                self._actions.get(action)()
                return True # Continue loop for other actions
        else:
            self.console.print(f"[bold red]Error: Unknown action '{action}'.[/bold red]")
            return True # Continue loop for unknown actions

    def run(self):
        while True:
            action = self.main_menu.run()
            
            # Handle invalid choice
            if action is None:
                self.console.print("[bold red]Invalid choice. Please try again.[/bold red]")
                self.console.input("[bold dim]Press Enter to continue...[/bold dim]")
                continue
            
            # Handle quit action
            if action == 'quit':
                self.run_action(action) # Call quit to print message
                break # Exit the loop directly for 'quit'

            # Execute the chosen action
            self.run_action(action)

            # clean up and return to main menu
            self.console.input("[bold dim]Press Enter to return to main menu...[/bold dim]")

if __name__ == "__main__":
    controller = Controller()
    controller.run()