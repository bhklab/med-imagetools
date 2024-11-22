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
def dicom_finder(
	search_input: str,
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

	dicom_files = find_dicoms(
		directory=path,
		check_header=check_header,
		recursive=True,
		extension=extension,
	)

	if not dicom_files:
		warningmsg = f'No DICOM files found in {path}.'
		logger.warning(
			warningmsg,
			directory=path,
			check_header=check_header,
			recursive=True,
			extension=extension,
		)
		return

	logger.info('DICOM find successful.', count=len(dicom_files))

	# Filter by multiple search patterns
	for search in search_input:
		try:
			pattern = re.compile(search)
			dicom_files = [f for f in dicom_files if pattern.search(str(f))]
			logger.info(
				f'Filtered files based on search_input "{search}".',
				search_input=search,
				filtered_count=len(dicom_files),
			)
		except re.error as e:
			errmsg = f'Invalid regex pattern "{search}": {str(e)}'
			logger.exception(errmsg)
			return

	if not dicom_files:
		warningmsg = f'Search input "{search_input}" did not match any DICOM files.'
		logger.warning(warningmsg)
		return

	if count:
		click.echo(f'Number of DICOM files found: {len(dicom_files)}')
		return

	if sort_results:
		dicom_files = sorted(dicom_files, key=lambda p: natural_sort_key(str(p)))

	if limit:
		dicom_files = dicom_files[:limit]

	for dicom_file in dicom_files:
		click.echo(dicom_file)

	logger.info('Search complete.')


if __name__ == '__main__':
	dicom_finder()
