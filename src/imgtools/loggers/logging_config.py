import json as jsonlib
import logging
import logging.config
import os
from pathlib import Path
from typing import Dict, List

import structlog
from structlog.processors import CallsiteParameter, CallsiteParameterAdder
from structlog.typing import Processor

from imgtools.loggers.processors import (
    CallPrettifier,
    ESTTimeStamper,
    PathPrettifier,
)

VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
DEFAULT_LOG_LEVEL = "WARNING"

LOG_DIR_NAME = Path(".imgtools/logs")


class LoggingManager:
    """
    Manages the configuration and initialization of a structured logger.

    This class provides flexible options for configuring log levels, formats,
    and output destinations.
    Examples
    --------
    Initialize with default settings:
        >>> manager = LoggingManager(name="mypackage")
        >>> logger = manager.get_logger()
        >>> logger.info("Info message")
    """

    def __init__(
        self,
        name: str,
        base_dir: Path | None = None,
    ) -> None:
        self.name = name
        self.base_dir = base_dir or Path.cwd()
        self.level = self.env_level
        self.enable_json_logging = (
            os.environ.get(f"{self.name}_enable_json_logging".upper(), "0")
            == "1"
        )
        self._initialize_logger()

    @property
    def env_level(self) -> str:
        return os.environ.get(
            f"{self.name}_LOG_LEVEL".upper(), DEFAULT_LOG_LEVEL
        ).upper()

    @property
    def base_logging_config(self) -> Dict:
        """
        Create the basic logging configuration settings.

        Returns
        -------
        dict
            Base logging configuration.
        """
        base = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "console": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processors": [
                        ESTTimeStamper(fmt="%H:%M:%S"),
                        CallPrettifier(concise=True),
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        structlog.dev.ConsoleRenderer(
                            colors=True,
                            sort_keys=False,
                            exception_formatter=structlog.dev.RichTracebackFormatter(
                                width=-1,
                                show_locals=False,
                            ),
                        ),
                    ],
                    "foreign_pre_chain": self.pre_chain,
                },
                "json": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processors": [
                        ESTTimeStamper(),
                        CallPrettifier(concise=False),
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        structlog.processors.dict_tracebacks,
                        structlog.processors.JSONRenderer(
                            serializer=jsonlib.dumps, indent=2
                        ),
                    ],
                    "foreign_pre_chain": self.pre_chain,
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "console",
                },
            },
            "loggers": {
                self.name: {
                    "handlers": ["console"],
                    "level": self.level,
                    "propagate": False,
                },
            },
        }

        if self.enable_json_logging:
            from datetime import datetime

            timestamped_logfile = (
                LOG_DIR_NAME
                / f"imgtools_{datetime.now():%Y-%m-%d_%H-%M-%S}.log"
            )
            # Ensure the log directory exists
            LOG_DIR_NAME.mkdir(parents=True, exist_ok=True)
            latest_symlink = LOG_DIR_NAME / "latest.log"
            if latest_symlink.exists() or latest_symlink.is_symlink():
                latest_symlink.unlink()
            latest_symlink.symlink_to(
                timestamped_logfile.name, target_is_directory=False
            )

            base["handlers"]["json"] = {  # type: ignore
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": timestamped_logfile,
                "maxBytes": 10485760,
                "backupCount": 5,
            }
            base["loggers"][self.name]["handlers"].append("json")  # type: ignore

        return base

    @property
    def pre_chain(self) -> List[Processor]:
        return [
            structlog.stdlib.add_log_level,
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
            structlog.processors.StackInfoRenderer(),
        ]

    def _initialize_logger(self) -> None:
        """
        Initialize the logger with the current configuration.
        """

        logging.config.dictConfig(self.base_logging_config)
        structlog.configure(
            processors=[
                *self.pre_chain,
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    def get_logger(self) -> structlog.stdlib.BoundLogger:
        """
        Retrieve the logger instance.

        Returns
        -------
        structlog.stdlib.BoundLogger
            Configured logger instance.
        """
        return structlog.get_logger(self.name)

    def configure_logging(
        self, level: str = DEFAULT_LOG_LEVEL
    ) -> structlog.stdlib.BoundLogger:
        """
        Dynamically adjust logging settings.

        Parameters
        ----------
        level : str, optional
            Set the log level.

        Returns
        -------
        structlog.stdlib.BoundLogger
            Updated logger instance.

        Raises
        ------
        ValueError
            If an invalid log level is specified.
        """
        level_upper = level.upper()
        if level_upper not in VALID_LOG_LEVELS:
            msg = f"Invalid logging level: {level}"
            raise ValueError(msg)

        # Store the old level for logging the change
        self.level = level_upper

        self._initialize_logger()
        logger = self.get_logger()

        return logger
