import pathlib
import re
from typing import List

import click

from imgtools.dicom import find_dicoms as find_dicoms_util
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
	nargs=-1,  # Allow multiple search inputs
	type=str,
	required=False,
)
@click.option(
	'-e',
	'--extension',
	default='dcm',
	show_default=True,
	help='File extension to look for.',
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
	'-ch',
	'--check-header',
	is_flag=True,
	default=False,
	show_default=True,
	help='Whether to check DICOM header for "DICM" signature.',
)
@click.option(
	'-s',
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
def find_dicoms(
	search_input: List[str],
	path: pathlib.Path,
	extension: str,
	check_header: bool,
	count: bool,
	limit: int,
	sort_results: bool,
) -> None:
	"""A tool to find DICOM files.

	PATH is the directory to search for DICOM files.

	SEARCH_INPUT is an optional list of regex patterns to filter the search results.

	"""
	logger.info('Searching for DICOM files.', args=locals())

	dicom_files = find_dicoms_util(
		directory=path,
		check_header=check_header,
		recursive=True,
		extension=extension,
		limit=limit,  # Pass limit parameter
		search_input=search_input,
	)

	if not dicom_files:
		warningmsg = f'No DICOM files found in {path}.'
		if not dicom_files:
			warningmsg += f' Search input "{search_input}" did not match any DICOM files.'
			warningmsg += ' Note: ALL search inputs must match to return a result.'
		logger.warning(
			warningmsg,
			directory=path,
			check_header=check_header,
			recursive=True,
			extension=extension,
			limit=limit,
			search_input=search_input,
		)
		return

	logger.info('DICOM find successful.', count=len(dicom_files))

	if count:
		click.echo(f'Number of DICOM files found: {len(dicom_files)}')
		return

	if sort_results:
		dicom_files = sorted(dicom_files, key=lambda p: natural_sort_key(str(p)))

	logger.info('Search complete.')

	for dicom_file in dicom_files:
		click.echo(dicom_file)



if __name__ == '__main__':
	find_dicoms()
