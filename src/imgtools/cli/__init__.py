from logging import ERROR, getLevelName, getLogger
from typing import Any, Callable

import click
from click.decorators import FC


def set_log_verbosity(
	*param_decls: str,
	logger_name: str = 'imgtools',
	quiet_decl: tuple = ('--quiet', '-q'),
	**kwargs: Any,  # noqa
) -> Callable[[FC], FC]:
	"""
	Add a `--verbose` option to set the logging level based on verbosity count
	and a `--quiet` option to suppress all logging except errors.

	Parameters
	----------
	*param_decls : str
		Custom names for the verbosity flag.
	quiet_decl : tuple
		Tuple containing custom names for the quiet flag.
	**kwargs : Any
		Additional keyword arguments for the click option.

	Returns
	-------
	Callable
		The decorated function with verbosity and quiet options.
	"""

	def callback(ctx: click.Context, param: click.Parameter, value: int) -> None:
		levels = {0: 'ERROR', 1: 'WARNING', 2: 'INFO', 3: 'DEBUG'}
		level = levels.get(value, 'DEBUG')  # Default to DEBUG if verbosity is high
		logger = getLogger(logger_name)
		# Check if `--quiet` is passed
		if ctx.params.get('quiet', False):
			logger.setLevel(ERROR)
			return

		levelvalue = getLevelName(level)
		env_level = logger.level

		# Override environment variable if verbosity level is passed
		if levelvalue > env_level and value != 0:
			logger.warning(
				f'Environment variable {logger.name.upper()}_LOG_LEVEL is {getLevelName(env_level)} but '
				f'you are setting it to {getLevelName(levelvalue)}'
			)
			logger.setLevel(levelvalue)
		else:
			logger.setLevel(min(levelvalue, env_level))

	# Default verbosity options
	if not param_decls:
		param_decls = ('--verbose', '-v')

	# Set default options for verbosity
	kwargs.setdefault('count', True)
	kwargs.setdefault(
		'help',
		'Increase verbosity of logging, overrides environment variable. '
		'(0-3: ERROR, WARNING, INFO, DEBUG).',
	)
	kwargs['callback'] = callback

	# Add the `--quiet` option
	def decorator(func: FC) -> FC:
		func = click.option(*param_decls, **kwargs)(func)
		func = click.option(*quiet_decl, is_flag=True, help='Suppress all logging except errors, overrides verbosity options.')(func)
		return func

	return decorator