"""Main entry point for the application."""
import os
import logging.config
import logging # Added for the test log message
from controller.main import MainMenuController
from config import config
from config.logging_config import LOGGING_CONFIG, LOG_DIR # Import LOG_DIR here as well

# Ensure the base log directory exists before configuring logging
os.makedirs(LOG_DIR, exist_ok=True)

# Apply the logging configuration
logging.config.dictConfig(LOGGING_CONFIG)

# Get a logger for the main module
logger = logging.getLogger(__name__)
logger.info("Application starting up and logging system initialized.") # Test log message

if __name__ == "__main__":
    #config.select_random_spinner()
    app = MainMenuController()
    app.run()
