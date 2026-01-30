"""
This module provides a command-line interface for managing database migrations
using Alembic. It allows for initialization of the Alembic environment,
creation of migration scripts, and application of those scripts.
"""

import logging
import sys
from pathlib import Path
import os
import shutil

from rich.console import Console  # Moved to module level

from config.config import PROJECT_ROOT

# Add project root to sys.path to allow imports from other modules like 'database'
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from alembic.config import Config
from alembic import command
from database.db_config import engine

logger = logging.getLogger(__name__)
console = Console()  # Instantiated at module level


class AlembicManager:
    """
    Provides methods to manage an Alembic migration environment programmatically.
    """

    def __init__(self):
        """Initializes the manager with project paths and the database engine."""
        self.project_root = PROJECT_ROOT
        self.alembic_dir = self.project_root / "alembic"
        self.alembic_ini_path = self.project_root / "alembic.ini"
        self.engine = engine
        logger.debug(f"AlembicManager initialized.")
        logger.debug(f"Project Root: {self.project_root}")
        logger.debug(f"Alembic directory: {self.alembic_dir}")
        logger.debug(f"Alembic INI: {self.alembic_ini_path}")

    def _generate_alembic_ini_content(self):
        """Generates the content for the alembic.ini file."""
        logger.debug("Generating alembic.ini content.")
        db_url = str(self.engine.url).replace("%", "%%")
        return f"""
[alembic]
script_location = alembic
salalchemy.url = {db_url}

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname = 

[logger_sqlalchemy]
level = WARN
handlers = 
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers = 
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""

    def _update_env_py(self):
        """
        Updates the alembic/env.py script to point to the project's models.
        """
        logger.debug("Updating alembic/env.py to point to project models.")
        env_py_path = self.alembic_dir / "env.py"
        if not env_py_path.exists():
            logger.error(
                f"Error: alembic/env.py not found at {env_py_path}! Cannot update."
            )
            return

        try:
            content = env_py_path.read_text()

            # Add project path and import Base
            path_and_import = (
                "import os\n"
                "import sys\n"
                "from pathlib import Path\n"
                "# Add project root to sys.path to find models\n"
                "sys.path.insert(0, str(Path(__file__).resolve().parents[1]))\n"
                "from database.models import Base"
            )

            original_line = "from logging.config import fileConfig"
            if "from database.models import Base" not in content:
                content = content.replace(
                    original_line, f"{path_and_import}\n\n{original_line}"
                )
                logger.debug("Added project path and model import to env.py.")

            # Set target_metadata
            content = content.replace(
                "target_metadata = None", "target_metadata = Base.metadata"
            )
            logger.debug("Set target_metadata to Base.metadata in env.py.")

            env_py_path.write_text(content)
            logger.info("Updated alembic/env.py successfully to use project models.")
        except Exception:
            logger.error(
                f"Failed to update alembic/env.py at {env_py_path}.", exc_info=True
            )

    def initialize_environment(self):
        """
        Initializes the Alembic environment if it doesn't exist.
        """
        logger.info("Initializing Alembic environment.")
        if self.alembic_ini_path.exists() and self.alembic_dir.exists():
            logger.info("Alembic environment already exists. Skipping initialization.")
            return

        try:
            # 1. Create alembic.ini
            self.alembic_ini_path.write_text(self._generate_alembic_ini_content())
            logger.info(f"Created {self.alembic_ini_path}")

            # 2. Create the alembic directory structure
            alembic_cfg = Config(str(self.alembic_ini_path))
            command.init(alembic_cfg, str(self.alembic_dir))
            logger.info(f"Created alembic directory at {self.alembic_dir}")

            # 3. Modify the env.py to point to our models
            self._update_env_py()

            # 4. Create an initial revision
            logger.info("Creating initial revision after environment setup.")
            self.create_revision("Initial migration")
            logger.info("Alembic environment initialized successfully.")
        except Exception:
            logger.error("Failed to initialize Alembic environment.", exc_info=True)

    def create_revision(self, message):
        """
        Creates a new revision file.
        --autogenerate compares models to the current DB state.
        """
        if not message:
            logger.error("Error: A message is required for the revision. Aborting.")
            return
        logger.info(f"Creating new Alembic revision with message: '{message}'.")
        alembic_cfg = Config(str(self.alembic_ini_path))
        try:
            command.revision(alembic_cfg, message=message, autogenerate=True)
            logger.info("Alembic revision created successfully.")
        except Exception:
            logger.error(
                f"Failed to create revision with message '{message}'.", exc_info=True
            )

    def upgrade_to_head(self):
        """Upgrades the database to the latest revision."""
        logger.info("Upgrading database to 'head' revision.")
        alembic_cfg = Config(str(self.alembic_ini_path))
        try:
            command.upgrade(alembic_cfg, "head")
            logger.info("Database upgraded successfully to 'head'.")
        except Exception:
            logger.error("Failed to upgrade database to 'head'.", exc_info=True)

    def downgrade_one(self):
        """Downgrades the database by one revision."""
        logger.info("Downgrading database by one revision.")
        alembic_cfg = Config(str(self.alembic_ini_path))
        try:
            command.downgrade(alembic_cfg, "-1")
            logger.info("Database downgraded successfully by one revision.")
        except Exception:
            logger.error("Failed to downgrade database by one revision.", exc_info=True)

    def reset_environment(self):
        """Deletes the alembic directory and config file."""
        logger.warning("Resetting Alembic environment (deleting files).")
        try:
            if self.alembic_dir.exists():
                shutil.rmtree(self.alembic_dir)
                logger.info(f"Removed directory: {self.alembic_dir}")
            if self.alembic_ini_path.exists():
                os.remove(self.alembic_ini_path)
                logger.info(f"Removed file: {self.alembic_ini_path}")
            logger.info("Alembic environment reset successfully.")
        except Exception:
            logger.error("Failed to reset Alembic environment.", exc_info=True)


def main_menu():
    """Displays the main menu and handles user interaction."""
    logger.info("Alembic Database Migration Menu started.")
    manager = AlembicManager()

    options = {
        "1": ("Initialize Alembic Environment", manager.initialize_environment),
        "2": (
            "Create New Migration (autogen)",
            lambda: manager.create_revision(input("Enter migration message: ")),
        ),
        "3": ("Upgrade to Latest Migration", manager.upgrade_to_head),
        "4": ("Downgrade by One Migration", manager.downgrade_one),
        "5": ("!!! RESET Alembic Environment !!!", manager.reset_environment),
        "q": ("Quit", lambda: sys.exit("Exiting.")),
    }

    while True:
        # For menu, console.print is appropriate for direct user interaction
        console.print("\n--- Alembic Database Migration Menu ---", style="bold yellow")
        for key, (desc, _) in options.items():
            console.print(f"  [cyan]{key}.[/cyan] {desc}", style="green")

        choice = input("Enter your choice: ").strip().lower()
        logger.debug("User selected menu option: '%s'", choice)

        if choice in options:
            desc, action = options[choice]
            logger.info(f"Executing menu action: {desc}")
            try:
                action()
            except SystemExit as e:
                logger.info(f"Exiting Alembic menu: {e}")
                print(e)  # Print exit message to console
                break
            except Exception:
                logger.error(
                    f"An error occurred while executing '{desc}'.", exc_info=True
                )
                console.print(
                    f"[bold red]An error occurred during migration: Check logs for details.[/bold red]"
                )
        else:
            logger.warning("Invalid choice in Alembic Migration Menu: '%s'", choice)
            console.print("[bold red]Invalid choice. Please try again.[/bold red]")


if __name__ == "__main__":
    main_menu()
