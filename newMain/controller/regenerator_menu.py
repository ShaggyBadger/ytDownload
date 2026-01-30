import logging
from rich.console import Console
from rich.prompt import Prompt

from services.evaluator import UserInteractiveEvaluator

logger = logging.getLogger(__name__)


class RegeneratorMenu:
    """
    A menu for evaluating regenerated paragraphs.
    """

    def __init__(self):
        self.console = Console()
        self.user_evaluator = UserInteractiveEvaluator(self.console)

    def run(self):
        """
        Displays the menu and handles user choices.
        """
        self.console.print("\n[bold cyan] Regenerator Menu [/bold cyan]")
        self.console.print("1. Evaluate a single job")
        self.console.print("2. Evaluate all eligible jobs")
        self.console.print("3. Back to main menu")

        choice = Prompt.ask("Choose an option", choices=["1", "2", "3"], default="3")

        if choice == "1":
            self.user_evaluator.evaluate_single_job()
        elif choice == "2":
            self.user_evaluator.evaluate_all_jobs()
        elif choice == "3":
            return
