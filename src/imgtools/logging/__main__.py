import logging
import time
import warnings
from contextlib import contextmanager

from tqdm import tqdm as std_tqdm
from tqdm.rich import tqdm_rich
from tqdm.std import TqdmExperimentalWarning
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    Text,
    TimeElapsedColumn,
    TimeRemainingColumn,
    filesize,
)

from typing import List, Optional, Type, Iterator
import logging
from imgtools.logging import logger, logging_manager
import sys
import structlog

warnings.filterwarnings("ignore", category=TqdmExperimentalWarning)
imgtools_logger = logging.getLogger("imgtools")

# create a custom structlog formatter with NO colors
_fmt = logging_manager.base_logging_config["formatters"]["console"]
print(_fmt["processors"])
formatter = structlog.stdlib.ProcessorFormatter(
    processor=structlog.dev.ConsoleRenderer(colors=False),
    foreign_pre_chain=_fmt["foreign_pre_chain"],
)


def _is_console_logging_handler(handler):
    return isinstance(handler, logging.StreamHandler) and handler.stream in {
        sys.stdout,
        sys.stderr,
    }


def _get_first_found_console_logging_handler(handlers):
    for handler in handlers:
        if _is_console_logging_handler(handler):
            return handler


# ruff : noqa


class _TqdmLoggingHandler(logging.StreamHandler):
    def __init__(
        self,
        tqdm_class=std_tqdm,  # type: Type[std_tqdm]
    ):
        super().__init__()
        self.tqdm_class = tqdm_class

    def emit(self, record):
        try:
            msg = self.format(record)

            self.tqdm_class.write(msg, file=self.stream)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:  # noqa pylint: disable=bare-except
            self.handleError(record)


@contextmanager
def logging_redirect_tqdm(
    loggers=None,  # type: Optional[List[logging.Logger]]
    tqdm_class=std_tqdm,  # type: Type[std_tqdm]
):
    # type: (...) -> Iterator[None]
    """
    Context manager redirecting console logging to `tqdm.write()`, leaving
    other logging handlers (e.g. log files) unaffected.

    Parameters
    ----------
    loggers  : list, optional
      Which handlers to redirect (default: [logging.root]).
    tqdm_class  : optional

    Example
    -------
    ```python
    import logging
    from tqdm import trange
    from tqdm.contrib.logging import (
        logging_redirect_tqdm,
    )

    LOG = logging.getLogger(__name__)

    if __name__ == "__main__":
        logging.basicConfig(level=logging.INFO)
        with logging_redirect_tqdm():
            for i in trange(9):
                if i == 4:
                    LOG.info(
                        "console logging redirected to `tqdm.write()`"
                    )
        # logging restored
    ```
    """
    if loggers is None:
        loggers = [logging.root]
    original_handlers_list = [logger.handlers for logger in loggers]
    try:
        for logger in loggers:
            tqdm_handler = _TqdmLoggingHandler(tqdm_class)
            orig_handler = _get_first_found_console_logging_handler(
                logger.handlers
            )
            if orig_handler is not None:
                tqdm_handler.setFormatter(orig_handler.formatter)
                # tqdm_handler.setFormatter(formatter)
                tqdm_handler.stream = orig_handler.stream
            logger.handlers = [
                handler
                for handler in logger.handlers
                if not _is_console_logging_handler(handler)
            ] + [tqdm_handler]
        yield
    finally:
        for logger, original_handlers in zip(loggers, original_handlers_list):
            logger.handlers = original_handlers


logger.setLevel(logging.DEBUG)
logger.debug("This is a debug message")
logger.info("This is an info message")
logger.warning("This is a warning message")
logger.error("This is an error message")
logger.critical("This is a critical message")

# create a rich progress bar to be used all over
progress = (
    "[progress.description]{task.description}"
    "[progress.percentage]{task.percentage:>4.0f}%",
    BarColumn(bar_width=None),
    "[",
    TimeElapsedColumn(),
    "<",
    TimeRemainingColumn(),
)


with logging_redirect_tqdm([imgtools_logger], tqdm_class=tqdm_rich):
    # Simulate multiple progress bars
    for i in tqdm_rich(range(4), desc="Processing 1", leave=False):
        if i == 2:
            logger.info("Halfway there in Processing 1!", step=i)
        time.sleep(0.5)

    for i in tqdm_rich(range(4), desc="Processing 2", leave=False):
        if i == 2:
            logger.info("Halfway there in Processing 2!", step=i)
        time.sleep(0.5)
