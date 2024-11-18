"""
This module provides a logging setup using structlog with custom processors for path prettification,
call information formatting, and timestamping in Eastern Standard Time.

Usage:
    Import the logger and use it directly:
    >>> from imgtools.logging import logger
    >>> logger.info('This is an info message', extra_field='extra_value')

    Or configure the logger with custom settings:
    >>> from imgtools.logging import get_logger, logging_manager

    # Change log level
    >>> logger = get_logger(level='DEBUG')

    # Configure multiple settings
    >>> logger = logging_manager.configure_logging(
    ...     json_logging=True,  # Enable JSON output to file
    ...     level='DEBUG',  # Set logging level
    ... )

Configuration:
    Environment variables:
    - IMGTOOLS_LOG_LEVEL: Set the default log level (default: 'INFO')
    - IMGTOOLS_JSON_LOGGING: Enable JSON logging to file (default: 'false')

    Output formats:
    - JSON output: Machine-parseable logs written to 'imgtools.log'
    - Console output: Human-readable logs with color-coded levels

    Log Levels:
    - DEBUG: Detailed information for debugging
    - INFO: General operational information
    - WARNING: Minor issues that don't affect operation
    - ERROR: Serious issues that affect operation
    - CRITICAL: Critical issues that require immediate attention
"""

import json as jsonlib
import logging.config
import os
from pathlib import Path
from typing import Optional

import structlog
from structlog.processors import CallsiteParameter, CallsiteParameterAdder

from imgtools.logging.processors import (
	CallPrettifier,
	ESTTimeStamper,
	PathPrettifier,
)

DEFAULT_LOG_LEVEL = 'INFO'


class LoggingManager:
	"""
	Manages the configuration and initialization of the logger.

	Args:
	    base_dir (Optional[Path]): The base directory for path prettification. Defaults to the current working directory.
				i.e if base_dir is /home/user/project and a path is /home/user/project/data/CT/1.dcm then the path will be data/CT/1.dcm for clarity
	"""

	def __init__(
		self,
		name: str,
		base_dir: Optional[Path] = None,
		level: str = os.environ.get('IMGTOOLS_LOG_LEVEL', DEFAULT_LOG_LEVEL),
		json_logging: bool = os.getenv('IMGTOOLS_JSON_LOGGING', 'false').lower() == 'true',
	) -> None:
		self.name = name
		self.base_dir = base_dir or Path.cwd()
		self.level = level.upper()
		self.json_logging = json_logging
		self.logger = None
		self._initialize_logger()

	# Modify _initialize_logger method to consider new options
	def _initialize_logger(self) -> None:
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

		if self.json_logging:
			log_dir = self.base_dir / '.imgtools' / 'logs'
			try:
				log_dir.mkdir(parents=True, exist_ok=True)
			except PermissionError as e:
				raise RuntimeError(f"Cannot create log directory at {log_dir}: {e}")
			except OSError as e:
				raise RuntimeError(f"Failed to create log directory at {log_dir}: {e}")
			json_log_file = str(log_dir / 'imgtools.log')

		logging_config = {
			'version': 1,
			'disable_existing_loggers': False,
			'formatters': {
				'console': {
					'()': structlog.stdlib.ProcessorFormatter,
					'processors': [
						CallPrettifier(concise=True),
						structlog.stdlib.ProcessorFormatter.remove_processors_meta,
						structlog.dev.ConsoleRenderer(
							exception_formatter=structlog.dev.RichTracebackFormatter(
								width=-1, show_locals=False
							),
						),
					],
					'foreign_pre_chain': pre_chain,
				},
				**(
					{
						'json': {
							'()': structlog.stdlib.ProcessorFormatter,
							'processors': [
								CallPrettifier(concise=False),
								structlog.stdlib.ProcessorFormatter.remove_processors_meta,
								structlog.processors.dict_tracebacks,
								structlog.processors.JSONRenderer(
									serializer=jsonlib.dumps, indent=2
								),
							],
							'foreign_pre_chain': pre_chain,
						}
					}
					if self.json_logging
					else {}
				),
			},
			'handlers': {
				'console': {
					'class': 'logging.StreamHandler',
					'formatter': 'console',
				},
				**(
					{
						'json': {
							'class': 'logging.FileHandler',
							'formatter': 'json',
							'filename': json_log_file,
						}
					}
					if self.json_logging
					else {}
				),
			},
			'loggers': {
				self.name: {
					'handlers': ['console'] + (['json'] if self.json_logging else []),
					'level': self.level,
					'propagate': False,
				},
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
			error_message = 'Logger has not been initialized.'
			raise RuntimeError(error_message)
		return self.logger

	# Add a method to dynamically adjust logging
	def configure_logging(
		self, json_logging: Optional[bool] = None, level: str = None
	) -> structlog.BoundLogger:
		if level is not None:
			self.level = level.upper()

		if self.level not in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
			error_message = f'Invalid logging level: {self.level}'
			raise ValueError(error_message)

		if json_logging is not None:
			self.json_logging = json_logging
		self._initialize_logger()

		return self.get_logger()


LOGGER_NAME = 'imgtools'
logging_manager = LoggingManager(LOGGER_NAME)


logger = logging_manager.configure_logging(level=DEFAULT_LOG_LEVEL)


def get_logger(level: str = 'INFO') -> logging.Logger:
	env_level = os.environ.get('IMGTOOLS_LOG_LEVEL', None)
	if env_level != level and env_level is not None:
		msg = f'environment variable IMGTOOLS_LOG_LEVEL is {env_level} but you are setting it to {level}'
		logger.warning(msg)
	return logging_manager.configure_logging(level=level)
