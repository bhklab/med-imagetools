from pathlib import Path

import click

from imgtools.cli import set_log_verbosity
from imgtools.dicom import find_dicoms
from imgtools.logging import logger


@click.command()
@set_log_verbosity()
@click.option(
	'--directory',
	'-d',
	type=click.Path(
		exists=True,
		file_okay=False,
		dir_okay=True,
		readable=True,
		resolve_path=True,
		path_type=Path,
	),
	help='Directory to search for DICOM files',
	required=True,
)
def main(directory: Path, verbose: int) -> None:
	extension = 'dcm'
	check_header = False
	logger.info('Searching for DICOM files.', args=locals())

	dicom_files = find_dicoms(
		directory=directory,
		check_header=check_header,
		recursive=True,
		extension=extension,
	)
	if not dicom_files:
		warningmsg = f'No DICOM files found in {directory}.'
		logger.warning(
			warningmsg,
			directory=directory,
			check_header=check_header,
			recursive=True,
			extension=extension,
		)
		return

	logger.info('DICOM find successful.', count=len(dicom_files))


if __name__ == '__main__':
	main()


# import pathlib
# import time
# from collections import defaultdict
# from concurrent.futures import ProcessPoolExecutor
# from contextlib import suppress
# from functools import partial
# from typing import Dict, List

# from pydicom import dcmread
# from pydicom.dataset import Dataset
# from tqdm import tqdm
# from tqdm.contrib.logging import logging_redirect_tqdm

# from imgtools.crawl.find_dicoms import find_dicoms

# def crawl_directory(
# 	top: pathlib.Path,
# 	extension: str = 'dcm',
# 	case_sensitive: bool = False,
# 	recursive: bool = True,
# 	check_header: bool = False,
# 	n_jobs: int = -1,
# ) -> Dict:
# 	start = time.time()

# 	dcms = find_dicoms(
# 		directory=top,
# 		case_sensitive=case_sensitive,
# 		recursive=recursive,
# 		check_header=check_header,
# 		extension=extension,
# 	)

# 	logger.info(f'Found {len(dcms)} DICOM files in {time.time() - start:.2f} seconds')

# 	database_list = []

# 	logger.info(
# 		f'Using {n_jobs} workers for parallel processing',
# 		param_n_jobs=n_jobs,
# 	)

# 	parse_dicom_partial = partial(parse_dicom, top=top)
# 	start = time.time()
# 	with (
# 		ProcessPoolExecutor(n_jobs) as executor,
# 		logging_redirect_tqdm([logging.getLogger('imgtools')]),
# 		tqdm(total=len(dcms), desc='Processing DICOM files') as pbar,
# 	):
# 		for database in executor.map(parse_dicom_partial, dcms):
# 			database_list.append(database)

# 			pbar.update(1)
# 	logger.info(
# 		f'Database: {len(database_list)} out of {len(dcms)} DICOM files in {time.time() - start:.2f} seconds'
# 	)
# 	# Combine all the JSON files into one
# 	logger.info('Combining JSON files...')
# 	db = _combine_jsons(database_list)
# 	return db
