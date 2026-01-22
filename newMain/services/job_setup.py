"""
This module provides services for ingesting video information into the database.
It defines functions to add new video entries and manage database sessions.
"""

from rich.console import Console
from database.session_manager import get_session
from database.models import VideoInfo


class ManualJobSetup:
    """Handles the setup of a single job provided manually."""
    def __init__(self):
        self.console = Console()

    def run(self):
        """The main execution method for the manual job setup flow."""
        self.console.print("[bold yellow]Service: ManualJobSetup is running.[/bold yellow]")
        # Placeholder for future logic (e.g., prompt for URL, process it)
        pass

class CsvJobSetup:
    """Handles the setup of jobs from a CSV file."""
    def __init__(self):
        self.console = Console()

    def run(self):
        """The main execution method for the CSV job setup flow."""
        self.console.print("[bold yellow]Service: CsvJobSetup is running.[/bold yellow]")
        # Placeholder for future logic (e.g., prompt for file path, process it)
        pass