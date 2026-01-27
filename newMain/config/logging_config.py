import os
import logging
import logging.handlers

# Define paths relative to the project root
LOG_DIR = 'logs'
ROTATING_LOGS_DIR = os.path.join(LOG_DIR, 'rotating_logs')

# Define log file paths
DEBUG_LOG_PATH = os.path.join(LOG_DIR, 'debug.log')
INFO_ROTATING_LOG_PATH = os.path.join(ROTATING_LOGS_DIR, 'app.log')

# Create directories if they don't exist
os.makedirs(ROTATING_LOGS_DIR, exist_ok=True)

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'handlers': {
        # Plain text, rotating INFO log
        'info_rotating_file_handler': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'standard',
            'filename': INFO_ROTATING_LOG_PATH,
            'maxBytes': 5 * 1024 * 1024,  # 5 MB
            'backupCount': 5,
            'encoding': 'utf8'
        },
        # Plain text, overwriting DEBUG log
        'debug_file_handler': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'standard',
            'filename': DEBUG_LOG_PATH,
            'mode': 'w',
            'encoding': 'utf8'
        },
    },
    'root': {
        'level': 'DEBUG',
        'handlers': [
            'info_rotating_file_handler',
            'debug_file_handler',
        ]
    }
}