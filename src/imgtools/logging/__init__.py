"""
Logging setup using structlog for path prettification, call information formatting,
and timestamping in Eastern Standard Time (EST).

This module provides a flexible and configurable logging framework with support for
human-readable console output and machine-parseable JSON logs.

Usage
-----
Basic usage:
    >>> from imgtools.logging import logger
    >>> logger.info('This is an info message', extra_field='extra_value')

Custom configuration:
    >>> from imgtools.logging import get_logger, logging_manager

    Change log level

    >>> logger = get_logger(level='DEBUG')

    Enable JSON logging

    >>> logger = logging_manager.configure_logging(
    ...     json_logging=True,  # Enable JSON output
    ...     level='DEBUG',  # Set logging level
    ... )

Configuration
-------------
Environment variables:
    IMGTOOLS_LOG_LEVEL : str, optional
        Default log level. Defaults to 'INFO'.
    IMGTOOLS_JSON_LOGGING : str, optional
        Enable JSON logging. Defaults to 'false'.

Output formats:
    - JSON: Machine-parseable logs written to `imgtools.log`.
    - Console: Human-readable logs with color-coded levels.

Log Levels:
    - DEBUG: Detailed information for debugging.
    - INFO: General operational information.
    - WARNING: Minor issues that don't affect operation.
    - ERROR: Serious issues that affect operation.
    - CRITICAL: Critical issues requiring immediate attention.

Classes
-------
LoggingManager
    Manages the configuration and initialization of the logger.

Functions
---------
get_logger(level: str = 'INFO') -> logging.Logger
    Retrieve a logger instance with the specified log level.
"""

import json as jsonlib
import logging.config
import os
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List

import structlog
from structlog.processors import CallsiteParameter, CallsiteParameterAdder

from imgtools.logging.processors import (
	CallPrettifier,
	ESTTimeStamper,
	PathPrettifier,
)

if TYPE_CHECKING:
	from structlog.typing import Processor

DEFAULT_LOG_LEVEL = 'INFO'
LOG_DIR_NAME = '.imgtools/logs'
DEFAULT_LOG_FILENAME = 'imgtools.log'
VALID_LOG_LEVELS = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}


class LoggingManager:
	"""
	Manages the configuration and initialization of a structured logger.

	This class provides flexible options for configuring log levels, formats,
	and output destinations. Logs can be human-readable or in JSON format for
	automated systems.

	Parameters
	----------
	name : str
	    Name of the logger instance.
	level : str, optional
	    Log level for the logger. Defaults to the environment variable
	    'IMGTOOLS_LOG_LEVEL' or 'INFO'.
	json_logging : bool, optional
	    Whether to enable JSON logging. Defaults to the environment variable
	    'IMGTOOLS_JSON_LOGGING' or `False`.
	base_dir : Path, optional
	    Base directory for relative path prettification. Defaults to the
	    current working directory.

	Attributes
	----------
	name : str
	    Name of the logger instance.
	base_dir : Path
	    Base directory for path prettification.
	level : str
	    Log level for the logger.
	json_logging : bool
	    Whether JSON logging is enabled.

	Methods
	-------
	get_logger()
	    Retrieve the configured logger instance.
	configure_logging(json_logging=None, level=None)
	    Dynamically adjust logging settings.

	Raises
	------
	ValueError
	    If an invalid log level is provided.
	RuntimeError
	    If the log directory or file cannot be created.

	Examples
	--------
	Initialize with default settings:
	    >>> manager = LoggingManager(name='mylogger')
	    >>> logger = manager.get_logger()
	    >>> logger.info('Info message')

	Enable JSON logging:
	    >>> manager = LoggingManager(name='mylogger', json_logging=True)
	    >>> logger = manager.get_logger()
	"""

	def __init__(
		self,
		name: str,
		level: str = os.environ.get('IMGTOOLS_LOG_LEVEL', DEFAULT_LOG_LEVEL),
		json_logging: bool = os.getenv('IMGTOOLS_JSON_LOGGING', 'false').lower() == 'true',
		base_dir: Path | None = None,
	) -> None:
		self.name = name
		self.base_dir = base_dir or Path.cwd()
		self.level = level.upper()
		self.json_logging = json_logging
		self._initialize_logger()

	def _setup_json_logging(self) -> str:
		"""
		Set up the logging configuration for JSON output.

		Ensures that the log directory exists and the log file is writable.

		Returns
		-------
		str
		    The path to the JSON log file.

		Raises
		------
		PermissionError
		    If the log file is not writable.
		RuntimeError
		    If the log directory cannot be created.
		"""
		try:
			log_dir = self.base_dir / LOG_DIR_NAME
			log_dir.mkdir(parents=True, exist_ok=True)
			json_log_file = log_dir / DEFAULT_LOG_FILENAME
			if json_log_file.exists() and not os.access(json_log_file, os.W_OK):
				msg = f'Log file {json_log_file} is not writable'
				raise PermissionError(msg)
		except (PermissionError, OSError) as err:
			msg = f'Failed to create log directory at {log_dir}: {err}'
			raise RuntimeError(msg) from err
		return str(json_log_file)

	def _create_base_logging_config(self, pre_chain: List) -> Dict:
		"""
		Create the basic logging configuration without JSON-specific settings.

		Parameters
		----------
		pre_chain : list
		    List of processors for structured logging.

		Returns
		-------
		dict
		    Base logging configuration.
		"""
		return {
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
			},
			'handlers': {
				'console': {
					'class': 'logging.StreamHandler',
					'formatter': 'console',
				},
			},
			'loggers': {
				self.name: {
					'handlers': ['console'],
					'level': self.level,
					'propagate': False,
				},
			},
		}

	def _add_json_logging_config(
		self, logging_config: Dict, pre_chain: List, json_log_file: str
	) -> Dict:
		"""
		Add JSON logging settings to the logging configuration.

		Parameters
		----------
		logging_config : dict
		    Existing logging configuration.
		pre_chain : list
		    List of processors for structured logging.
		json_log_file : str
		    Path to the JSON log file.

		Returns
		-------
		dict
		    Updated logging configuration.
		"""
		json_formatter = {
			'json': {
				'()': structlog.stdlib.ProcessorFormatter,
				'processors': [
					CallPrettifier(concise=False),
					structlog.stdlib.ProcessorFormatter.remove_processors_meta,
					structlog.processors.dict_tracebacks,
					structlog.processors.JSONRenderer(serializer=jsonlib.dumps, indent=2),
				],
				'foreign_pre_chain': pre_chain,
			},
		}
		json_handler = {
			'json': {
				'class': 'logging.handlers.RotatingFileHandler',
				'formatter': 'json',
				'filename': json_log_file,
				'maxBytes': 10485760,
				'backupCount': 5,
			},
		}

		logging_config['formatters'].update(json_formatter)
		logging_config['handlers'].update(json_handler)
		logging_config['loggers'][self.name]['handlers'].append('json')
		return logging_config

	def _initialize_logger(self) -> None:
		"""
		Initialize the logger with the current configuration.
		"""
		pre_chain: List[Processor] = [
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
			structlog.processors.StackInfoRenderer(),
		]

		logging_config = self._create_base_logging_config(pre_chain)

		if self.json_logging:
			json_log_file = self._setup_json_logging()
			logging_config = self._add_json_logging_config(logging_config, pre_chain, json_log_file)

		logging.config.dictConfig(logging_config)
		structlog.configure(
			processors=[
				*pre_chain,
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
		self, json_logging: bool = False, level: str = DEFAULT_LOG_LEVEL
	) -> structlog.stdlib.BoundLogger:
		"""
		Dynamically adjust logging settings.

		Parameters
		----------
		json_logging : bool, default=False
		    Enable or disable JSON logging.
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
		if level is not None:
			if level not in VALID_LOG_LEVELS:
				msg = f'Invalid logging level: {level}'
				raise ValueError(msg)
			self.level = level.upper()

		if json_logging is not None:
			self.json_logging = json_logging
		self._initialize_logger()

		return self.get_logger()


LOGGER_NAME = 'imgtools'
logging_manager = LoggingManager(LOGGER_NAME)
logger = logging_manager.configure_logging(level=DEFAULT_LOG_LEVEL)


def get_logger(level: str = 'INFO') -> structlog.stdlib.BoundLogger:
	"""
	Retrieve a logger with the specified log level.

	Parameters
	----------
	level : str
	    Desired logging level.

	Returns
	-------
	logging.Logger
	    Configured logger instance.
	"""
	env_level = os.environ.get('IMGTOOLS_LOG_LEVEL', None)
	if env_level != level and env_level is not None:
		logger.warning(
			f'Environment variable IMGTOOLS_LOG_LEVEL is {env_level} '
			f'but you are setting it to {level}'
		)
	return logging_manager.configure_logging(level=level)
