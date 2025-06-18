# import json as jsonlib
# self.json_logging = (
# 	self._get_env_variable(f'{name}_JSON_LOGGING', 'false').lower() == 'true'
# )
# def _setup_json_logging(self) -> str:
# 	"""
# 	Set up the logging configuration for JSON output.

# 	Ensures that the log directory exists and the log file is writable.

# 	Returns
# 	-------
# 	str
# 	    The path to the JSON log file.

# 	Raises
# 	------
# 	PermissionError
# 	    If the log file is not writable.
# 	RuntimeError
# 	    If the log directory cannot be created.
# 	"""
# 	try:
# 		log_dir = self.base_dir / LOG_DIR_NAME
# 		log_dir.mkdir(parents=True, exist_ok=True)
# 		json_log_file = log_dir / DEFAULT_LOG_FILENAME
# 		if json_log_file.exists() and not os.access(json_log_file, os.W_OK):
# 			msg = f'Log file {json_log_file} is not writable'
# 			raise PermissionError(msg)
# 	except (PermissionError, OSError) as err:
# 		msg = f'Failed to create log directory at {log_dir}: {err}'
# 		raise RuntimeError(msg) from err
# 	return str(json_log_file)

# def _add_json_logging_config(
# 	self, logging_config: Dict, pre_chain: List, json_log_file: str
# ) -> Dict:
# 	"""
# 	Add JSON logging settings to the logging configuration.

# 	Parameters
# 	----------
# 	logging_config : dict
# 	    Existing logging configuration.
# 	pre_chain : list
# 	    List of processors for structured logging.
# 	json_log_file : str
# 	    Path to the JSON log file.

# 	Returns
# 	-------
# 	dict
# 	    Updated logging configuration.
# 	"""
# 	json_formatter = {
# 		'json': {
# 			'()': structlog.stdlib.ProcessorFormatter,
# 			'processors': [
# 				CallPrettifier(concise=False),
# 				structlog.stdlib.ProcessorFormatter.remove_processors_meta,
# 				structlog.processors.dict_tracebacks,
# 				structlog.processors.JSONRenderer(serializer=jsonlib.dumps, indent=2),
# 			],
# 			'foreign_pre_chain': pre_chain,
# 		},
# 	}
# 	json_handler = {
# 		'json': {
# 			'class': 'logging.handlers.RotatingFileHandler',
# 			'formatter': 'json',
# 			'filename': json_log_file,
# 			'maxBytes': 10485760,
# 			'backupCount': 5,
# 		},
# 	}

# 	logging_config['formatters'].update(json_formatter)
# 	logging_config['handlers'].update(json_handler)
# 	logging_config['loggers'][self.name]['handlers'].append('json')
# 	return logging_config


# if self.json_logging:
# 	json_log_file = self._setup_json_logging()
# 	logging_config = self._add_json_logging_config(logging_config, pre_chain, json_log_file)
