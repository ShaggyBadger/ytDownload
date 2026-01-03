import logging
import os
from logging.handlers import RotatingFileHandler

# --- Configuration ---
LOG_LEVEL = logging.DEBUG # Set your desired global log level here

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # Create handlers
    stream_handler = logging.StreamHandler()
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=1024*1024*5, backupCount=5)

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
