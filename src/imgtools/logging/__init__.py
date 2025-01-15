import os
from pathlib import Path

import structlog

from imgtools.logging.logging_config import DEFAULT_LOG_LEVEL, LoggingManager

# Set the default log level from the environment variable or use the default
DEFAULT_OR_ENV = os.environ.get("IMGTOOLS_LOG_LEVEL", DEFAULT_LOG_LEVEL)

LOG_DIR_NAME = Path(".imgtools/logs")
DEFAULT_LOG_FILENAME = "imgtools.log"


def get_logger(name: str, level: str = "INFO") -> structlog.stdlib.BoundLogger:
    """
    Retrieve a logger with the specified log level.

    Parameters
    ----------
    name : str
                    Name of Logger Instance
    level : str
        Desired logging level.

    Returns
    -------
    logging.Logger
        Configured logger instance.
    """
    logging_manager = LoggingManager(name)
    env_level = logging_manager.env_level

    if env_level not in (level, DEFAULT_LOG_LEVEL):
        logging_manager.get_logger().warning(
            f"Environment variable {name}_LOG_LEVEL is {env_level} "
            f"but you are setting it to {level}"
        )
    return logging_manager.configure_logging(level=level)


logger = get_logger("imgtools", DEFAULT_OR_ENV)


if __name__ == "__main__":
    # Example usage of the logging manager
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

    readii_logger = get_logger("readii", "DEBUG")
    readii_logger.debug("This is a debug message")
    readii_logger.info("This is an info message")
    readii_logger.warning("This is a warning message")
    readii_logger.error("This is an error message")
