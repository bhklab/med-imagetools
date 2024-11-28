from typing import Any, Callable
from click.decorators import FC
from logging import getLevelName

import click
from imgtools.logging import logger

def set_log_verbosity(
	*param_decls: str,
	**kwargs: Any,  # noqa
) -> Callable[[FC], FC]:
	"""Add a `--verbose` option to set the logging level based on verbosity count."""

	def callback(ctx: click.Context, param: click.Parameter, value: int) -> None:
		levels = {0: 'ERROR', 1: 'WARNING', 2: 'INFO', 3: 'DEBUG'}
		level = levels.get(value, 'DEBUG')  # Default to DEBUG if verbosity is high
		logger.setLevel(getLevelName(level))

	if not param_decls:
		param_decls = ('--verbose', '-v')

	kwargs.setdefault('count', True)
	kwargs.setdefault(
		'help',
		'Increase verbosity of logging, overrides environment variable. (0-3: ERROR, WARNING, INFO, DEBUG).',
	)
	kwargs['callback'] = callback
	return click.option(*param_decls, **kwargs)
