# agriconnect-refactored/common/logger_config.py

import logging
import sys
from pathlib import Path
from common.settings import settings

LOG_FILE_PATH = Path("app.log") # Default log file name

class ContextualFormatter(logging.Formatter):
    """
    A custom formatter that adds the 'filename' and 'funcName' to the log record.
    """
    def format(self, record):
        # Add filename and function name to the log record's __dict__
        # This makes them available in the format string.
        record.filename = Path(record.pathname).name # Get just the filename
        record.funcName = record.funcName
        return super().format(record)

def setup_logging():
    """
    Sets up the application-wide logging configuration.
    Configures handlers for console and file logging.
    """
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Clear any existing handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # Define the log format, including filename and function name
    # Format: TIMESTAMP [LEVEL] [FILENAME:LINENO] MESSAGE
    log_format = "%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s"
    formatter = ContextualFormatter(log_format)

    # 1. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. File Handler
    # Ensure the log directory exists (though for a single file in the root, this is simple)
    LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(LOG_FILE_PATH, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Set the log level for the root logger to INFO
    logger.setLevel(logging.INFO)

    # Informational message about the logging setup
    logger.info(f"Logging initialized. Console logs enabled. File logs directed to: {LOG_FILE_PATH.resolve()}")

# Call setup_logging() to apply the configuration
setup_logging()

# Export the log file path for the gateway to use
__all__ = ["LOG_FILE_PATH"]