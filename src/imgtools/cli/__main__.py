from logging import getLevelName
from typing import Any, Callable

import click
from click.decorators import FC

from imgtools import __version__
from imgtools.cli.dicomfind import dicom_finder
from imgtools.cli.dicomsort import dicomsort
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


@click.group(
	no_args_is_help=True,
)
@set_log_verbosity()
@click.version_option(
	version=__version__,
	package_name='med-imagetools',
	prog_name='imgtools',
	message='%(package)s:%(prog)s:%(version)s',
)
@click.help_option(
	'-h',
	'--help',
)
def cli(verbose: int) -> None:
	"""A collection of tools for working with medical imaging data."""
	pass


cli.add_command(dicomsort)
cli.add_command(dicom_finder, 'find-dicoms')

if __name__ == '__main__':
	cli()
