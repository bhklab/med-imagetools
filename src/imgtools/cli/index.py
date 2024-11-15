import json
import os
import pathlib
from typing import Dict

import click

from imgtools import __version__
from imgtools.crawl.crawl import crawl_directory
from imgtools.logging import logger


@click.command()
@click.option(
	'--extension',
	'-e',
	default='dcm',
	help='File extension to search for (default: dcm).',
)
@click.option(
	'--case-sensitive',
	is_flag=True,
	help='Search for files case-sensitively.',
)
@click.option(
	'--recursive',
	'-r',
	default=True,
	is_flag=True,
	help='Search for files recursively.',
)
@click.option(
	'--check-header',
	is_flag=True,
	default=False,
	help='Check for DICOM header after preamble.',
)
@click.option(
	'--jobs',
	'-j',
	default=os.cpu_count(),
	help=f'Number of parallel jobs to use (default:{os.cpu_count()}).',
)
@click.argument(
	'directory',
	type=click.Path(
		exists=True,
		path_type=pathlib.Path,
		resolve_path=True,
		file_okay=False,
		readable=True,
	),
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
def index(
	directory: pathlib.Path,
	extension: str,
	check_header: bool,
	recursive: bool,
	case_sensitive: bool,
	jobs: int,
) -> None:
	"""Generate an index of DICOM files in a directory.

		Crawls a directory to index DICOM files and saves the resulting database to a JSON file.

	Parameters
	----------
	directory : pathlib.Path
			The directory to crawl.
	extension : str
			The file extension to look for (e.g., 'dcm').
	check_header : bool
			Whether to check the DICOM header.
	recursive : bool
			Whether to crawl directories recursively.
	case_sensitive : bool
			Whether the file extension matching is case sensitive.
	jobs : int
			The number of parallel jobs to use for processing.

	Returns
	-------
	None

	Notes
	-----
	This function saves the resulting database to a JSON file in the directory.
	"""

	logger.debug('Crawling directory:', directory=directory)

	db = crawl_directory(
		top=directory,
		extension=extension,
		case_sensitive=case_sensitive,
		recursive=recursive,
		check_header=check_header,
		n_jobs=jobs,
	)

	output_file = directory / 'dataset.json'
	logger.debug('Saving database to JSON file...', file=output_file)

	write_json(db, output_file)


def write_json(db: Dict, output_file: pathlib.Path) -> None:
	"""
	Writes a dictionary to a JSON file.

	Args:
	    db (Dict): The dictionary to serialize and write.
	    output_file (pathlib.Path): Path to the output file.
	"""
	try:
		with output_file.open('w') as f:
			json.dump(db, f, indent=4)
	except (TypeError, PermissionError, IsADirectoryError, Exception) as e:
		error_type = type(e).__name__
		logger.exception(
			f'{error_type} occurred while writing to file',
			exc_info=e,
		)
		msg = f'{error_type} occurred while writing to {output_file}: {e}'
		raise IOError(msg) from e


if __name__ == '__main__':
	index()
