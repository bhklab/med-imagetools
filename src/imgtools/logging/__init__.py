"""
This module provides a logging setup using structlog with custom processors for path prettification,
call information formatting, and timestamping in Eastern Standard Time.

Usage:
    Import the logger and use it to log messages in your package.

    from readii.logging import logger

    logger.info("This is an info message", extra_field="extra_value")

    The logger can output in JSON format or console format based on whether the output is a TTY.

    - JSON output: Suitable for structured logging and machine parsing.
    - Console output: Suitable for human-readable logs during development.

Classes:
    LoggingManager: Manages the configuration and initialization of the logger.
"""

from collections import defaultdict
import structlog
import json as jsonlib
import logging.config

from structlog.processors import CallsiteParameterAdder, CallsiteParameter

from imgtools.logging.processors import (
    PathPrettifier,
    ESTTimeStamper,
    CallPrettifier,
)
from pathlib import Path
from typing import Optional


class LoggingManager:
    """
    Manages the configuration and initialization of the logger.

    Args:
        base_dir (Optional[Path]): The base directory for path prettification. Defaults to the current working directory.
    """

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        level: str = "DEBUG",
    ):
        self.base_dir = base_dir or Path.cwd()
        self.level = level
        self.logger = None
        self._initialize_logger()

    def _initialize_logger(self):
        """
        Initializes the logger with the appropriate processors based on the output format.
        """
        pre_chain = [
            structlog.stdlib.add_log_level,
            ESTTimeStamper(),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            CallsiteParameterAdder(
                [
                    CallsiteParameter.MODULE,
                    CallsiteParameter.FUNC_NAME,
                    CallsiteParameter.LINENO,
                ]
            ),
            PathPrettifier(base_dir=self.base_dir),
            structlog.stdlib.ExtraAdder(),
        ]

        processors = [
            *pre_chain,
            structlog.processors.StackInfoRenderer(),
        ]

        logging_config = defaultdict()
        logging_config["version"] = 1
        logging_config["disable_existing_loggers"] = False

        logging_config["formatters"] = {
            "console": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": [
                    CallPrettifier(concise=True),
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.dev.ConsoleRenderer(
                        # pad_event=50,
                        exception_formatter=structlog.dev.RichTracebackFormatter(
                            width=-1, show_locals=False
                        ),
                    ),
                ],
                "foreign_pre_chain": pre_chain,
            },
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": [
                    CallPrettifier(concise=False),
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.processors.dict_tracebacks,
                    structlog.processors.JSONRenderer(
                        serializer=jsonlib.dumps, indent=2
                    ),
                ],
                "foreign_pre_chain": pre_chain,
            },
        }

        logging_config["handlers"] = {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
            },
            "json": {
                "class": "logging.FileHandler",
                "formatter": "json",
                "filename": self.base_dir / "imgtools.log",
            },
        }

        logging_config["loggers"] = {
            # TURN THIS ON IF YOU WANT ROOT LOGGER TO PRINT NICE LOGS AS WELL!
            # "": {
            #     "handlers": ["console"],
            #     "level": self.level,
            #     "propagate": False,
            # },
            "imgtools": {
                "handlers": ["console", "json"],
                "level": self.level,
                "propagate": False,
            },
        }
        logging.config.dictConfig(logging_config)

        structlog.configure_once(
            processors=[
                *processors,
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=False,
        )
        self.logger = structlog.get_logger("imgtools")
        # self.logger = logging.getLogger("imgtools")

    def get_logger(self) -> structlog.stdlib.BoundLogger:
        """
        Returns the initialized logger.

        Returns:
            structlog.BoundLogger: The initialized logger.

        Raises:
            RuntimeError: If the logger has not been initialized.
        """
        if not self.logger:
            raise RuntimeError("Logger has not been initialized.")
        return self.logger


logging_manager = LoggingManager()

logger = logging_manager.get_logger()
