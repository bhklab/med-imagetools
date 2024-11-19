import click

from imgtools import __version__
from imgtools.cli.index import index
from imgtools.logging import logger


def set_logging_level(verbosity: int) -> None:
	"""Sets logging level based on verbosity count."""
	levels = {0: 'ERROR', 1: 'WARNING', 2: 'INFO', 3: 'DEBUG'}
	level = levels.get(verbosity, 'DEBUG')  # Default to DEBUG if verbosity is high
	logger.setLevel(level)


@click.group()
@click.option(
	'--verbose',
	'-v',
	count=True,
	help='Increase verbosity of logging, overrides environment variable. (0-3: ERROR, WARNING, INFO, DEBUG).',
)
@click.version_option(
	version=__version__,
	package_name='med-imagetools',
	prog_name='mit',
	message='%(package)s:%(prog)s:%(version)s',
)
@click.help_option(
	'-h',
	'--help',
)
@click.option('--debug/--no-debug', default=False)
def cli(verbose: int, debug: bool) -> None:
	set_logging_level(verbose)


cli.add_command(index, name='index')

if __name__ == '__main__':
	cli()
