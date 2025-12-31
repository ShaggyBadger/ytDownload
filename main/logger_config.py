import logging
import logging.handlers

def setup_logging():
    """
    Sets up a centralized logger for the application.
    """
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO) # Set the lowest level for the logger

    # Prevent propagation to the default handler to avoid duplicate logs in console
    if logger.hasHandlers():
        logger.handlers.clear()

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO) # Log INFO and above to console
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    # Use a rotating file handler to keep log files from growing too large
    file_handler = logging.handlers.RotatingFileHandler(
        'app.log', maxBytes=5*1024*1024, backupCount=2
    )
    file_handler.setLevel(logging.DEBUG) # Log DEBUG and above to file
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logging.info("Logging configured.")
