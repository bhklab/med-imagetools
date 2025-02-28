import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

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


@contextmanager
def temporary_log_level(
    logger: structlog.stdlib.BoundLogger, level: str
) -> Generator[None, Any, None]:
    """
    Temporarily change the log level of a logger within a context.

    Parameters
    ----------
    logger : structlog.stdlib.BoundLogger
        The logger instance to modify
    level : str
        The temporary log level to set

    Examples
    --------
    >>> with temporary_log_level(logger, "ERROR"):
    ...     # Only ERROR and CRITICAL messages will be logged in this block
    ...     logger.warning("This won't be logged")
    ...     logger.error("This will be logged")
    """
    import logging

    original_level = logger.level
    logger.setLevel(getattr(logging, level.upper()))
    try:
        yield
    finally:
        logger.setLevel(original_level)


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

    with temporary_log_level(logger, "WARNING"):
        logger.debug("This won't be logged")
        logger.info("This won't be logged")
        logger.warning("This SHOULD be logged")
        logger.error("This will be logged")
        logger.critical("This will be logged")
