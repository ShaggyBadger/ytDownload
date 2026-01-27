import os
import logging
import logging.handlers

# Define paths relative to the project root
LOG_DIR = 'logs'
ROTATING_LOGS_DIR = os.path.join(LOG_DIR, 'rotating_logs')
ROTATING_LOGS_COLOR_DIR = os.path.join(LOG_DIR, 'rotating_logs_color') # New dir for color rotating logs

# Define log file paths
DEBUG_LOG_PATH = os.path.join(LOG_DIR, 'debug.log')
DEBUG_COLOR_LOG_PATH = os.path.join(LOG_DIR, 'debug_color.log')
INFO_ROTATING_LOG_PATH = os.path.join(ROTATING_LOGS_DIR, 'app.log')
INFO_COLOR_ROTATING_LOG_PATH = os.path.join(ROTATING_LOGS_COLOR_DIR, 'app.log') # New path for color rotating log

# Create directories if they don't exist
os.makedirs(ROTATING_LOGS_DIR, exist_ok=True)
os.makedirs(ROTATING_LOGS_COLOR_DIR, exist_ok=True) # Create the new directory

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'color': {
            '()': 'colorlog.ColoredFormatter',
            'format': '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
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
        # Colorized, overwriting DEBUG log
        'debug_color_file_handler': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'color',
            'filename': DEBUG_COLOR_LOG_PATH,
            'mode': 'w',
            'encoding': 'utf8'
        },
        # Colorized, rotating INFO log (New)
        'info_color_rotating_file_handler': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'color',
            'filename': INFO_COLOR_ROTATING_LOG_PATH,
            'maxBytes': 5 * 1024 * 1024,  # 5 MB
            'backupCount': 5,
            'encoding': 'utf8'
        }
    },
    'root': {
        'level': 'DEBUG',
        'handlers': [
            'info_rotating_file_handler',
            'debug_file_handler',
            'debug_color_file_handler',
            'info_color_rotating_file_handler' # Added the new handler
        ]
    }
}
