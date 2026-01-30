import logging

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from controller import job_setup
from controller import job_download
from controller import whisper_deploy_menu
from controller import format_transcription
from controller import editor_controller
from controller.chapter_builder_menu import ChapterBuilderMenu
from controller.evaluator_controller import EvaluatorMenu
from config import config

from controller import metadata_generator

logger = logging.getLogger(__name__)


class MainMenuController:
    """
    Top-level CLI menu for the sermon pipeline program, using Rich for visuals.
    Encapsulates the main menu logic and handles user interaction to navigate
    to different parts of the application.
    """

    def __init__(self):
        self.console = Console()
        self.options = {
            "1": {"desc": "Job Setup Menu", "func": self._run_job_setup_menu},
            "2": {
                "desc": "Download and Trim Jobs",
                "func": self._run_job_download_menu,
            },
            "3": {
                "desc": "Deploy/Retrieve Jobs to Server",
                "func": self._run_whisper_deployment,
            },
            "4": {"desc": "Format Textblocks", "func": self._run_formatter},
            "5": {"desc": "Generate Metadata", "func": self._run_metadata_menu},
            "6": {"desc": "Edit Transcript", "func": self._run_editor_menu},
            "7": {
                "desc": "Run Paragraph Evaluation",
                "func": self._run_evaluation_menu,
            },
            "8": {"desc": "Build Chapter", "func": self._run_chapter_builder_menu},
            "q": {"desc": "Exit", "func": None},
        }
        logger.debug("MainMenuController initialized with options.")

    def _run_evaluation_menu(self):
        """Runs the evaluator menu."""
        logger.info("Dispatching to Evaluator Menu.")
        try:
            evaluator_menu = EvaluatorMenu()
            evaluator_menu.run()
            logger.info("Returned from Evaluator Menu.")
        except Exception:
            logger.error("Error encountered in Evaluator Menu.", exc_info=True)

    def _run_chapter_builder_menu(self):
        """Runs the chapter builder menu."""
        logger.info("Dispatching to Chapter Builder Menu.")
        try:
            chapter_builder_menu_instance = ChapterBuilderMenu()
            chapter_builder_menu_instance.run()
            logger.info("Returned from Chapter Builder Menu.")
        except Exception:
            logger.error("Error encountered in Chapter Builder Menu.", exc_info=True)

    def _run_editor_menu(self):
        """Runs the editor menu."""
        logger.info("Dispatching to Editor Menu.")
        try:
            editor_menu = editor_controller.EditorMenu()
            editor_menu.run()
            logger.info("Returned from Editor Menu.")
        except Exception:
            logger.error("Error encountered in Editor Menu.", exc_info=True)

    def _run_metadata_menu(self):
        """Runs the metadata controller"""
        logger.info("Dispatching to Metadata Generator Menu.")
        try:
            metadata_generator.metadata_generator_menu()
            logger.info("Returned from Metadata Generator Menu.")
        except Exception:
            logger.error("Error encountered in Metadata Generator Menu.", exc_info=True)

    def _run_job_setup_menu(self):
        """Instantiates and runs the job setup controller."""
        logger.info("Dispatching to Job Setup Menu.")
        try:
            setup_controller = job_setup.JobSetupController()
            setup_controller.run()
            logger.info("Returned from Job Setup Menu.")
        except Exception:
            logger.error("Error encountered in Job Setup Menu.", exc_info=True)

    def _run_job_download_menu(self):
        """Instantiates and runs the job download controller"""
        logger.info("Dispatching to Job Download Menu.")
        try:
            download_controller = job_download.JobDownloadController()
            download_controller.run()
            logger.info("Returned from Job Download Menu.")
        except Exception:
            logger.error("Error encountered in Job Download Menu.", exc_info=True)

    def _run_whisper_deployment(self):
        """Activates script to deploy jobs to the server for transcription"""
        logger.info("Dispatching to Whisper Deployment Menu.")
        try:
            deployment_controller = whisper_deploy_menu.Menu()
            deployment_controller.run()
            logger.info("Returned from Whisper Deployment Menu.")
        except Exception:
            logger.error("Error encountered in Whisper Deployment Menu.", exc_info=True)

    def _run_formatter(self):
        """Activates script to format whisperAI slop into nice paragraphs"""
        logger.info("Dispatching to Formatter Menu.")
        try:
            format_controller = format_transcription.FormatTranscriptionController()
            format_controller.run()
            logger.info("Returned from Formatter Menu.")
        except Exception:
            logger.error("Error encountered in Formatter Menu.", exc_info=True)

    def run(self):
        """
        Displays the main menu and handles user choices.
        """
        logger.info("MainMenuController started. Displaying main menu.")
        while True:
            console = self.console

            console.clear()
            console.rule("[bold blue]Sermon Pipeline Main Menu[/bold blue]")

            table = Table(
                title="Available Options",
                show_header=True,
                header_style="bold magenta",
                box=config.BOX_STYLE,
                padding=(0, 2),
            )
            table.add_column("Option", style="cyan", width=8)
            table.add_column("Action", style="green")

            for key, val in self.options.items():
                table.add_row(key, val["desc"])

            console.print(table)

            choice = Prompt.ask("[bold yellow]Select an option[/bold yellow]").strip()
            logger.info("User selected option: '%s'", choice)

            selected_option = self.options.get(choice)

            if selected_option is None:
                logger.warning("User entered invalid choice: '%s'", choice)
                console.print(
                    "[red]Invalid choice. Please select a valid option.[/red]"
                )
                console.input("Press Enter to continue...")
                continue

            action_func = selected_option.get("func")

            if action_func is None:
                logger.info("User chose to exit the application. Goodbye!")
                console.print("[bold red]Goodbye![/bold red]")
                break

            logger.info("Executing: %s", selected_option.get("desc"))
            try:
                action_func()
            except Exception:
                logger.critical(
                    f"An unhandled error occurred while running '{selected_option.get('desc')}'",
                    exc_info=True,
                )
                console.print(
                    f"[bold red]An unexpected error occurred while running '{selected_option.get('desc')}'. Check logs for details.[/bold red]"
                )
                console.input("Press Enter to continue...")
