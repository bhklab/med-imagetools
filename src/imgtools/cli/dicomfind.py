import pathlib
import re

import click

from imgtools.dicom import find_dicoms
from imgtools.logging import logger


def natural_sort_key(s: str) -> list:
	"""Sort strings in a natural order."""
	return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]


@click.command()
@click.argument(
	'path',
	type=click.Path(
		exists=True,
		file_okay=False,
		dir_okay=True,
		readable=True,
		path_type=pathlib.Path,
		resolve_path=True,
	),
)
@click.argument(
	'search_input',
	required=False,
	type=str,
)
@click.option(
	'-e',
	'--extension',
	default='dcm',
	show_default=True,
	help='File extension to look for.',
)
@click.option(
	'--check-header',
	is_flag=True,
	default=False,
	show_default=True,
	help='Whether to check DICOM header for "DICM" signature.',
)
@click.option(
	'-c',
	'--count',
	is_flag=True,
	default=False,
	show_default=True,
	help='Whether to just print the count of files found. This is useful for scripts.',
)
@click.option(
	'-l',
	'--limit',
	default=None,
	type=int,
	show_default=True,
	help='The limit of results to return.',
)
@click.option(
	'--sorted',
	'sort_results',
	is_flag=True,
	default=False,
	show_default=True,
	help='Sort the results alphabetically.',
)
@click.help_option(
	'-h',
	'--help',
)
def dicom_finder(
	path: pathlib.Path,
	search_input: str,
	extension: str,
	check_header: bool,
	count: bool,
	limit: int,
	sort_results: bool,
) -> None:
	"""A tool to find DICOM files."""
	logger.info('Searching for DICOM files.', args=locals())

	dicom_files = find_dicoms(
		directory=path,
		check_header=check_header,
		recursive=True,
		extension=extension,
	)
	logger.info('DICOM find successful.', count=len(dicom_files))

	if sort_results:
		dicom_files = sorted(dicom_files, key=natural_sort_key)

	if limit:
		dicom_files = dicom_files[:limit]

	if count:
		click.echo(f'Number of DICOM files found: {len(dicom_files)}')
	else:
		for dicom_file in dicom_files:
			click.echo(dicom_file)

	logger.info('Search complete.')


if __name__ == '__main__':
	dicom_finder()
