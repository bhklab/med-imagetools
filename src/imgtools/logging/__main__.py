import time
from imgtools.logging import logger
import click
import logging
from tqdm import trange
from tqdm.contrib.logging import logging_redirect_tqdm, tqdm_logging_redirect


@click.command()
def main():
    """
    Create and configure an example structlog logger.
    """
    logger.debug(
        "This is a debug message",
    )
    logger.info(
        "This is an info message",
    )
    logger.warning(
        "This is a warning message",
    )
    logger.error(
        "This is an error message",
    )
    logger.critical(
        "This is a critical message",
    )
    logger.fatal(
        "This is a fatal message",
    )

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("This is an exception message")

    # To use tqdm with logger,
    # you need to get the logger from base logging instead of structlog
    imgtools_logger = logging.getLogger("imgtools")
    imgtools_logger.info("This is an imgtools logger message")
    imgtools_logger.warning("This is an imgtools logger warning message")
    imgtools_logger.error("This is an imgtools logger error message")

    with logging_redirect_tqdm([imgtools_logger]):
        for i in trange(4):
            imgtools_logger.info(f"This is a tqdm logger message {i}")
            time.sleep(0.5)
            if i == 3:
                1 / 0


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception(e)