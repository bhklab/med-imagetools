import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Generator, List, TypeVar

import tqdm
from pydicom import dcmread
from pydicom.errors import InvalidDicomError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from imgtools.dicom.index.models import (
	File,
	Patient,
	Series,
	Study,
	mapper_registry,
)
from imgtools.logging import get_logger

logger = get_logger('DICOMIndexer', 'DEBUG')


def _extract_metadata(file_path: Path, tags: List[str]) -> Dict[str, str]:
	"""
	need to -> benchmark against `read_tags` function in `utils.py`
	"""

	try:
		dicom = dcmread(file_path, specific_tags=tags, stop_before_pixels=True)
	except FileNotFoundError as fnfe:
		errmsg = f'File not found: {file_path}'
		raise FileNotFoundError(errmsg) from fnfe
	except InvalidDicomError as ide:
		errmsg = f'Invalid DICOM file: {file_path}'
		raise InvalidDicomError(errmsg) from ide
	except ValueError as ve:
		errmsg = f'Value error reading DICOM file: {file_path}'
		raise ValueError(errmsg) from ve

	return {tag: str(dicom.get(tag, '')) for tag in tags}


class DatabaseHandler:
	"""
	Manages database operations using SQLAlchemy ORM.
	"""

	def __init__(self, db_path: Path, force_delete: bool = False) -> None:
		"""
		Initialize the DatabaseHandler with an SQLite database.

		Parameters
		----------
		db_path : Path
			Path to the SQLite database file.
		force_delete : bool
			Whether to delete the existing database file if it exists.
		"""
		if force_delete and db_path.exists():
			db_path.unlink()  # Delete the existing database file

		self.engine = create_engine(f'sqlite:///{db_path}', future=True)
		mapper_registry.metadata.create_all(self.engine)  # Create tables
		self.Session = sessionmaker(bind=self.engine)

	@contextmanager
	def session(self) -> Generator[Session, None, None]:
		"""
		Create a new SQLAlchemy session.

		Yields
		------
		Session
			A SQLAlchemy session object.
		"""
		session = self.Session()
		try:
			yield session
			session.commit()  # Commit the transaction
		except Exception:
			session.rollback()  # Rollback on exception
			raise
		finally:
			session.close()

class DICOMIndexer:
	"""
	A tool to index DICOM files and insert metadata into the database.
	"""

	def __init__(self, db_handler: DatabaseHandler) -> None:
		"""
		Initialize the DICOMIndexer.

		Parameters
		----------
		db_handler : DatabaseHandler
				An instance of DatabaseHandler for managing database operations.
		"""
		self.db_handler = db_handler
		self.mytags = [
			'PatientID',
			'StudyInstanceUID',
			'SeriesInstanceUID',
			'Modality',
			'SOPInstanceUID',
		]

	def _insert_patient(self, session: Session, metadata: Dict[str, str]) -> Patient:
		patient = session.query(Patient).filter_by(PatientID=metadata['PatientID']).first()
		if not patient:
			patient = Patient.from_metadata(metadata)
			session.add(patient)
		return patient

	def _insert_study(self, session: Session, metadata: Dict[str, str]) -> Study:
		study = (
			session.query(Study).filter_by(StudyInstanceUID=metadata['StudyInstanceUID']).first()
		)
		if not study:
			study = Study.from_metadata(metadata)
			session.add(study)
		return study

	def _insert_series(self, session: Session, metadata: Dict[str, str]) -> Series:
		series = (
			session.query(Series).filter_by(SeriesInstanceUID=metadata['SeriesInstanceUID']).first()
		)
		if not series:
			series = Series.from_metadata(metadata)
			session.add(series)
		return series

	def _insert_file(self, session: Session, metadata: Dict[str, str], file_path: Path) -> File:
		file = session.query(File).filter_by(SOPInstanceUID=metadata['SOPInstanceUID']).first()
		if not file:
			file = File.from_metadata(metadata, file_path)
			session.add(file)
		return file

	@property
	def existing_files(self) -> List[Path]:
		"""
		Get a list of file paths already indexed in the database.

		Returns
		-------
		List[Path]
				A list of file paths.
		"""
		with self.db_handler.session() as session:
			return [Path(file.FilePath) for file in session.query(File.FilePath).all()]

	def build_index_from_files(self, files: List[Path]) -> None:
		"""
		Build an index of DICOM files and insert metadata into the database.

		Parameters
		----------
		files : List[Path]
				List of file paths to index.
		"""
		existing_files = self.existing_files
		remaining_files = list(set(files) - set(existing_files))
		logger.debug(f'{len(existing_files)} files already indexed.')
		logger.debug(f'{len(remaining_files)}/{len(files)} files left to index.')

		if not remaining_files:
			logger.info('All files are already indexed.')
			return
		start = time.time()
		try:
			with (
				self.db_handler.session() as session,
				tqdm.tqdm(
					total=len(remaining_files),
					initial=len(existing_files),
					desc='Indexing DICOM files',
				) as tqdm_files,
			):
				for file_path in remaining_files:
					metadata = _extract_metadata(file_path, self.mytags)
					_ = self._insert_patient(session, metadata)
					_ = self._insert_study(session, metadata)
					series = self._insert_series(session, metadata)
					file = self._insert_file(session, metadata, file_path)
					# series.files.append(file)
					tqdm_files.update(1)
		except Exception as e:
			logger.exception(f'Error: {e}')
			raise e
		finally:
			logger.info(f'Indexing complete in {time.time() - start:.2f} seconds.')

T = TypeVar('T')  # Generic type for table models


class DICOMDatabaseInterface:
	"""
	A class to interact with the DICOM database and perform high-level operations.
	"""

	def __init__(self, db_handler: DatabaseHandler) -> None:
		"""
		Initialize the database interface.

		Parameters
		----------
		db_handler : DatabaseHandler
			An instance of DatabaseHandler for managing database operations.
		"""
		self.session = db_handler.Session()

	@property
	def patients(self) -> List[Patient]:
		return self.session.query(Patient).all()

	@property
	def studies(self) -> List[Study]:
		return self.session.query(Study).all()

	@property
	def series(self) -> List[Series]:
		return self.session.query(Series).all()

	





if __name__ == '__main__':
	from pathlib import Path

	from imgtools.dicom import find_dicoms
	from imgtools.logging import get_logger

	logger = get_logger('INDEXER', 'DEBUG')

	directory = Path('/Users/bhklab/dev/radiomics/med-imagetools/data/nbia/images/unzipped')
	db_path = Path('dicom_index.sqlite')
	db_handler = DatabaseHandler(db_path=db_path)
	check_header = False
	extension = 'dcm'

	logger.info('Finding DICOM files...')
	dicom_files = find_dicoms(
		directory=directory,
		check_header=check_header,
		recursive=True,
		extension=extension,
	)
	logger.info(f'Found {len(dicom_files)} DICOM files.')


	indexer = DICOMIndexer(db_handler=db_handler)

	# Build index
	indexer.build_index_from_files(dicom_files)


	# Query the database
	db = DICOMDatabaseInterface(db_handler=db_handler)
	from rich import print

	start = time.time()
	print(db.patients[0])
	print('-'*50)
	print(db.studies[0])
	print('-'*50)
	print(db.series[0])
	print('-'*50)
	print(db.series[0].files[0])
	print(f'Querying complete in {time.time() - start:.2f} seconds.')
	print(db.series[0].files[0].series.study.patient)