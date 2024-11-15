import json
import os
import pathlib
import sys
from collections import Counter

import click

from imgtools.crawl.crawl import crawl_directory
from imgtools.logging import logger

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.command(context_settings=CONTEXT_SETTINGS)
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
	'--n-jobs',
	'-j',
	default=-1,
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
@click.argument(
	'output_file',
	type=click.Path(
		exists=False,
		path_type=pathlib.Path,
		resolve_path=True,
		file_okay=True,
		writable=True,
		dir_okay=False,
	),
)
def main(
	directory: pathlib.Path,
	output_file: pathlib.Path,
	extension: str,
	check_header: bool,
	recursive: bool,
	case_sensitive: bool,
	n_jobs: int,
) -> None:
	logger.debug('Starting crawl', locals=locals())
	logger.debug('Crawling directory:', directory=directory)

	db = crawl_directory(
		top=directory,
		extension=extension,
		case_sensitive=case_sensitive,
		recursive=recursive,
		check_header=check_header,
		n_jobs=n_jobs,
	)

	# NOTE: these stats are temporary and will be remove

	# Group by PatientID and count occurrences
	patient_counts = Counter(entry['PatientID'] for entry in db)
	modality_counts = Counter(entry['Modality'] for entry in db)
	unique_modality_series = [
		(entry['Modality'], entry['SeriesInstanceUID']) for entry in db
	]
	pair_counts = Counter(unique_modality_series)

	# Convert the result to a dictionary or print it
	logger.info(f'Found {len(patient_counts)} patients')

	logger.info('DICOMS per Modality', modalities=modality_counts)

	logger.info('Series per Modality', counts=Counter(m for m, _ in pair_counts))

	# NOTE: End note.

	# Save list of dicts to JSON file
	logger.debug('Saving database to JSON file...', file=output_file)
	try:
		with output_file.open('w') as f:
			f.write(json.dumps(db, indent=4))
	except PermissionError as pe:
		logger.exception(
			'Permission denied to write to file', exception=pe, file=output_file
		)
		sys.exit(1)
	except IsADirectoryError as iade:
		logger.exception(
			'output_file is a directory already',
			exception=iade,
			file=output_file,
		)
		sys.exit(1)


if __name__ == '__main__':
	main()
