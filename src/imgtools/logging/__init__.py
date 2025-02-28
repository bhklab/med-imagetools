import os
from contextlib import _GeneratorContextManager
from pathlib import Path

import structlog
from tqdm.contrib.logging import logging_redirect_tqdm

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


def tqdm_logging_redirect(
    logger_name: str = "imgtools",
) -> _GeneratorContextManager[None, None, None]:
    """Context manager to redirect logging output into tqdm for cleaner logging.

    Parameters
    ----------
    logger_name : str, optional
        The name of the logger to redirect, by default "imgtools".

    Returns
    -------
    logging_redirect_tqdm
        A context manager that redirects logging output.

    Examples
    --------
    >>> from tqdm import tqdm
    >>> import time
    >>> with tqdm_logging_redirect():
    ...     for i in tqdm(range(10), desc="Processing"):
    ...         logger.info(f"Processing {i}")
    ...         time.sleep(0.1)
    """
    import logging

    return logging_redirect_tqdm([logging.getLogger(logger_name)])


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

    import time  # noqa
    from tqdm import tqdm

    with tqdm_logging_redirect():
        for i in tqdm(range(10), desc="Processing"):
            logger.info(f"Processing {i}")
            time.sleep(0.1)
