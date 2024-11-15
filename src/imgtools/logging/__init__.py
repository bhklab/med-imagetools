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
import os

DEFAULT_LOG_LEVEL = "INFO"

class LoggingManager:
    """
    Manages the configuration and initialization of the logger.

    Args:
        base_dir (Optional[Path]): The base directory for path prettification. Defaults to the current working directory.
    """

    def __init__(
        self,
        name: str,
        base_dir: Optional[Path] = None,
        level: str = os.environ.get("IMGTOOLS_LOG_LEVEL", DEFAULT_LOG_LEVEL),
        json_logging: bool = os.getenv("IMGTOOLS_JSON_LOGGING", "false").lower() == "true",
    ):
        self.name = name
        self.base_dir = base_dir or Path.cwd()
        self.level = level
        self.json_logging = json_logging
        self.logger = None
        self._initialize_logger()

    # Modify _initialize_logger method to consider new options
    def _initialize_logger(self):
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

        # Configure formatters based on `console_logging` and `json_logging`
        logging_config["formatters"] = {}
        logging_config["formatters"]["console"] = {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                CallPrettifier(concise=True),
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(
                    exception_formatter=structlog.dev.RichTracebackFormatter(
                        width=-1, show_locals=False
                    ),
                ),
            ],
            "foreign_pre_chain": pre_chain,
        }

        if self.json_logging:
            logging_config["formatters"]["json"] = {
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
            }

        # Configure handlers based on available formatters
        logging_config["handlers"] = {}

        logging_config["handlers"]["console"] = {
            "class": "logging.StreamHandler",
            "formatter": "console",
        }

        if self.json_logging:
            logging_config["handlers"]["json"] = {
                "class": "logging.FileHandler",
                "formatter": "json",
                "filename": self.base_dir / "imgtools.log",
            }
        logging_config["loggers"] = {
            self.name: {
                "handlers": [
                    handler
                    for handler in ("console", "json")
                    if handler in logging_config["handlers"]
                ],
                "level": self.level,
                "propagate": False,
            },
        }

        logging.config.dictConfig(logging_config)
        structlog.configure(
            processors=[
                *processors,
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=False,
        )
        self.logger = structlog.get_logger(self.name)

    def get_logger(self) -> structlog.stdlib.BoundLogger:
        if not self.logger:
            raise RuntimeError("Logger has not been initialized.")
        return self.logger

    # Add a method to dynamically adjust logging
    def configure_logging(
        self, json_logging: Optional[bool] = None, level: str = None
    ) -> structlog.BoundLogger:
        if level is not None:
            self.level = level.upper()

        if self.level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            raise ValueError(f"Invalid logging level: {self.level}")

        if json_logging is not None:
            self.json_logging = json_logging
        self._initialize_logger()

        return self.get_logger()

LOGGER_NAME = "imgtools"
logging_manager = LoggingManager(LOGGER_NAME)

def get_logger(LEVEL: str = "INFO") -> logging.Logger:
    return logging_manager.configure_logging(level=LEVEL)

logger = logging_manager.configure_logging(level=DEFAULT_LOG_LEVEL)
