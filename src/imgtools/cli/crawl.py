import json
import pathlib
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
	'-cs',
	is_flag=True,
	help='Search for files case-sensitively.',
)
@click.option(
	'--n-jobs',
	'-j',
	default=-1,
	help='Number of parallel jobs to use (default: number of CPU cores).',
)
@click.argument(
	'directory',
	type=click.Path(
		exists=True,
		path_type=pathlib.Path,
		resolve_path=True,
		file_okay=False,
	),
)
def main(
	directory: pathlib.Path,
	extension: str,
	case_sensitive: bool,
	n_jobs: int,
) -> None:
	logger.debug('Starting crawl', locals=locals())
	logger.debug('Crawling directory:', directory=directory)

	db = crawl_directory(
		top=directory,
		extension=extension,
		case_sensitive=case_sensitive,
		n_jobs=n_jobs,
	)

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
	# logger.info('Series per Modality', counts=Counter(m for m, _ in pair_counts.keys()))

	# Save list of dicts to JSON file
	output = pathlib.Path('database.json')
	with output.open('w') as f:
		logger.debug('Saving database to JSON file...', file=output)
		f.write(json.dumps(db, indent=4))


if __name__ == '__main__':
	main()
