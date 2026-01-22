"""
This module provides a command-line interface for managing database migrations
using Alembic. It allows for initialization of the Alembic environment,
creation of migration scripts, and application of those scripts.
"""

import sys
from pathlib import Path
import os
import shutil

from config.config import PROJECT_ROOT
# Add project root to sys.path to allow imports from other modules like 'database'
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from alembic.config import Config
from alembic import command
from database.db_config import engine

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
        print(f"Project Root: {self.project_root}")
        print(f"Alembic directory: {self.alembic_dir}")
        print(f"Alembic INI: {self.alembic_ini_path}")


    def _generate_alembic_ini_content(self):
        """Generates the content for the alembic.ini file."""
        db_url = str(self.engine.url).replace('%', '%%')
        return f"""
[alembic]
script_location = alembic
sqlalchemy.url = {db_url}

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
        env_py_path = self.alembic_dir / "env.py"
        if not env_py_path.exists():
            print("Error: alembic/env.py not found!")
            return

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

        # Make the replacement more robust
        original_line = "from logging.config import fileConfig"
        if "from database.models import Base" not in content:
            content = content.replace(original_line, f"{path_and_import}\n\n{original_line}")

        # Set target_metadata
        content = content.replace("target_metadata = None", "target_metadata = Base.metadata")

        env_py_path.write_text(content)
        print("Updated alembic/env.py to use project models.")

    def initialize_environment(self):
        """
        Initializes the Alembic environment if it doesn't exist.
        """
        print("Initializing Alembic environment...")
        if self.alembic_ini_path.exists() and self.alembic_dir.exists():
            print("Alembic environment already exists.")
            return

        # 1. Create alembic.ini
        self.alembic_ini_path.write_text(self._generate_alembic_ini_content())
        print(f"Created {self.alembic_ini_path}")

        # 2. Create the alembic directory structure
        alembic_cfg = Config(str(self.alembic_ini_path))
        command.init(alembic_cfg, str(self.alembic_dir))
        print(f"Created alembic directory at {self.alembic_dir}")

        # 3. Modify the env.py to point to our models
        self._update_env_py()
        
        # 4. Create an initial revision
        print("Creating initial revision...")
        self.create_revision("Initial migration")

    def create_revision(self, message):
        """
        Creates a new revision file.
        --autogenerate compares models to the current DB state.
        """
        if not message:
            print("Error: A message is required for the revision.")
            return
        print(f"Creating revision: {message}...")
        alembic_cfg = Config(str(self.alembic_ini_path))
        try:
            command.revision(alembic_cfg, message=message, autogenerate=True)
            print("Revision created successfully.")
        except Exception as e:
            print(f"Failed to create revision: {e}")

    def upgrade_to_head(self):
        """Upgrades the database to the latest revision."""
        print("Upgrading database to 'head'...")
        alembic_cfg = Config(str(self.alembic_ini_path))
        try:
            command.upgrade(alembic_cfg, "head")
            print("Database upgraded successfully.")
        except Exception as e:
            print(f"Failed to upgrade: {e}")

    def downgrade_one(self):
        """Downgrades the database by one revision."""
        print("Downgrading database by one revision...")
        alembic_cfg = Config(str(self.alembic_ini_path))
        try:
            command.downgrade(alembic_cfg, "-1")
            print("Database downgraded successfully.")
        except Exception as e:
            print(f"Failed to downgrade: {e}")

    def reset_environment(self):
        """Deletes the alembic directory and config file."""
        print("Resetting Alembic environment...")
        if self.alembic_dir.exists():
            shutil.rmtree(self.alembic_dir)
            print(f"Removed directory: {self.alembic_dir}")
        if self.alembic_ini_path.exists():
            os.remove(self.alembic_ini_path)
            print(f"Removed file: {self.alembic_ini_path}")
        print("Environment reset.")


def main_menu():
    """Displays the main menu and handles user interaction."""
    manager = AlembicManager()

    options = {
        "1": ("Initialize Alembic Environment", manager.initialize_environment),
        "2": ("Create New Migration (autogen)", lambda: manager.create_revision(input("Enter migration message: "))),
        "3": ("Upgrade to Latest Migration", manager.upgrade_to_head),
        "4": ("Downgrade by One Migration", manager.downgrade_one),
        "5": ("!!! RESET Alembic Environment !!!", manager.reset_environment),
        "q": ("Quit", lambda: sys.exit("Exiting."))
    }

    while True:
        print("\n--- Alembic Database Migration Menu ---")
        for key, (desc, _) in options.items():
            print(f"  {key}. {desc}")
        
        choice = input("Enter your choice: ").strip().lower()

        if choice in options:
            _, action = options[choice]
            try:
                action()
            except SystemExit as e:
                print(e)
                break
            except Exception as e:
                print(f"An error occurred: {e}")
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main_menu()
