import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

# --- Configuration ---
LOG_LEVEL = logging.DEBUG # Set your desired global log level here

# Determine the project's base directory (which is the parent of the 'main' directory)
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / 'logs'
LOG_FILE = LOG_DIR / 'app.log'

# Create logs directory if it doesn't exist
LOG_DIR.mkdir(exist_ok=True)

def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # Avoid adding handlers multiple times if the logger is already configured
    if logger.hasHandlers():
        return logger

    # Create handlers
    stream_handler = logging.StreamHandler()
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1024*1024*5, backupCount=5)

    # Create formatters and add it to handlers
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(log_format)
    file_handler.setFormatter(log_format)

    # Set levels for handlers explicitly to ensure they respect the global setting
    stream_handler.setLevel(LOG_LEVEL)
    file_handler.setLevel(LOG_LEVEL)

    # Add handlers to the logger
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    return logger
