
import json
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Type, Union

import pandas as pd
import tqdm
from sqlitedict import SqliteDict

from imgtools.dicom import find_dicoms
from imgtools.dicom.sort.utils import read_tags
from imgtools.logging import logger

logger.setLevel('DEBUG')

def _extract_metadata(file_path: Path) -> Dict[str, str]:
	"""
	Extract relevant metadata from a DICOM file.

	Parameters
	----------
	file_path : pathlib.Path
		Path to the DICOM file.

	Returns
	-------
	Dict[str, Optional[str]]
		Metadata including patient ID, study instance UID, and series instance UID.
	"""
	tags_of_interest = [
		'PatientID',
		'StudyInstanceUID',
		'SeriesInstanceUID',
		'Modality',
		'AccessionNumber',
	]
	# Simulating read_tags for simplicity; replace with actual implementation
	return read_tags(file_path, tags_of_interest, truncate=False, sanitize=False)

class DICOMIndexer:
	"""
	A tool to index DICOM files in a directory, storing metadata in an SQLite-based dictionary.

	Attributes
	----------
	db_path : pathlib.Path 
		Path to the SQLite file used by SqliteDict.
	"""

	def __init__(self, db_path: Path) -> None:
		"""
		Initialize the DICOMIndexer with a database path.

		Parameters
		----------
		db_path : pathlib.Path 
			Path to the SQLite file used by SqliteDict.
		"""
		db_path = Path(db_path)
		logger.info('Initializing DICOMIndexer', extra={'db_path': db_path})
		self.db_path = db_path
		self.file_db = SqliteDict(
			self.db_path,
			autocommit=True,
			tablename='files',
		)

	def build_index_from_files(self, files: List[Path], max_workers: int = 4) -> None:
		"""
		Build an index of DICOM files from a list of file paths using multithreading.

		Parameters
		----------
		files : List[Union[str, Path]]
			List of file paths to index.
		max_workers : int, optional
			Maximum number of worker threads, by default 4.
		"""
		logger.info('Building index from files', extra={'count': len(files)})

		existing_files = set(self.file_db.keys())

		logger.info('Filtering out existing files', extra={'count': len(existing_files)})

		# Filter out files that are already in the database
		files_to_process = [file for file in files if file.as_posix() not in existing_files]

		with (
			ProcessPoolExecutor(
				max_workers=max_workers
			) as executor, 
			tqdm.tqdm(
				total = len(files),
				initial = len(existing_files),
			) as pbar,
		):
			future_to_file = {
				file_path: executor.submit(_extract_metadata, file_path)
				for file_path in files_to_process
			}
			for future in as_completed(future_to_file.values()):
				file_path = next(key for key, value in future_to_file.items() if value == future)
				try:
					self.file_db[file_path.as_posix()] = future.result()
					pbar.update(1)
				except Exception as e:
					logger.error('Error processing file', extra={'file_path': file_path, 'error': str(e)})

		logger.info('Indexing complete.')

	def patients(self: 'DICOMIndexer') -> List[str]:
		"""
		Get a list of unique patient IDs in the index.

		Returns
		-------
		List[str]
			A list of unique patient IDs.
		"""
		patients = set()
		with self.file_db as db:
			for metadata in db.values():
				patients.add(metadata['PatientID'])
		return list(patients)

	def filter_by_modality(self: 'DICOMIndexer', modality: str) -> List[str]:
		"""
		Filter the index by modality.

		Parameters
		----------
		modality : str
			The modality to filter by.

		Returns
		-------
		List[str]
			A list of file paths that match the specified modality.
		"""
		with self.file_db as db:
			return [
				file_path for file_path, metadata in db.items()
				if metadata['Modality'] == modality
			]

def main() -> None:
	# directory = Path("/Users/bhklab/dev/radiomics/med-imagetools/data/nbia/images/unzipped/")
	# check_header = False
	# extension = 'dcm'
	# dicom_files = find_dicoms(
	# 		directory=directory,
	# 		check_header=check_header,
	# 		recursive=True,
	# 		extension=extension,
	# )
	# logger.info(f"Found {len(dicom_files)} DICOM files.")
	indexer = DICOMIndexer(db_path=Path('dicom_index.sqlite'))

	patients = indexer.patients()
	logger.info(f"Found {len(patients)} unique patients.")

	for modality in ['CT', 'MR', 'SEG', 'RTSTRUCT']:
		files = indexer.filter_by_modality(modality)
		logger.info(f"Found {len(files)} {modality} files.")

	import time
	start = time.time()
	# Create a pandas DataFrame from the file_db entries	
	with indexer.file_db as db:
		data = [
			{'file_path': file_path, **metadata}
			for file_path, metadata in db.items()
		]

	df = pd.DataFrame(data)

	# Save the DataFrame to a CSV file
	df.to_csv('files.csv', index=False)
	logger.info(f'Took {time.time() - start:.2f} seconds to save file database to files.csv')
	logger.info('Saved file database to files.csv')

	# total_files_in_db = len(indexer.file_db)
	# indexer.build_index_from_files(dicom_files, max_workers=i)
	# import time
	# n_workers = 10
	# logger.info(f"Building index with {n_workers} workers.")
	# start = time.time()
	# indexer.build_index_from_files(dicom_files, max_workers=n_workers)
	# logger.info(f"Indexing complete in {time.time() - start:.2f} seconds with {n_workers} workers.")



if __name__ == "__main__":

	main()
	# indexer = DICOMIndexer(db_path='dicom_index.sqlite')
	# indexer.build_index_from_files(dicom_files)
	# print(indexer.patients())
	# indexer.file_db.close()