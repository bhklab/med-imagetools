from pathlib import Path
from typing import List

import pandas as pd
import tqdm
from sqlalchemy import Column, Date, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeMeta, Session, declarative_base, relationship, sessionmaker

# from imgtools.dicom import find_dicoms
from imgtools.dicom.sort.utils import read_tags
from imgtools.logging import get_logger

logger = get_logger("extract", "DEBUG")

Base: DeclarativeMeta = declarative_base()

class Patient(Base):
	"""
	ORM model for the Patients table.
	"""
	__tablename__ = 'patients'
	PatientID = Column(String, primary_key=True)
	PatientName = Column(String, nullable=True)
	DOB = Column(Date, nullable=True)

	studies: relationship = relationship("Study", back_populates="patient")


class Study(Base):
	"""
	ORM model for the Studies table.
	"""
	__tablename__ = 'studies'
	StudyInstanceUID = Column(String, primary_key=True)
	PatientID = Column(String, ForeignKey('patients.PatientID'), nullable=False)
	StudyDate = Column(Date, nullable=True)
	Description = Column(String, nullable=True)

	patient: relationship = relationship("Patient", back_populates="studies")
	series: relationship = relationship("Series", back_populates="study")


class Series(Base):
	"""
	ORM model for the Series table.
	"""
	__tablename__ = 'series'
	SeriesInstanceUID = Column(String, primary_key=True)
	StudyInstanceUID = Column(String, ForeignKey('studies.StudyInstanceUID'), nullable=False)
	Modality = Column(String, nullable=False)
	Description = Column(String, nullable=True)

	study: relationship = relationship("Study", back_populates="series")
	files: relationship = relationship("File", back_populates="series")


class File(Base):
	"""
	ORM model for the Files table.
	"""
	__tablename__ = 'files'
	SOPInstanceUID = Column(String, primary_key=True)
	SeriesInstanceUID = Column(String, ForeignKey('series.SeriesInstanceUID'), nullable=False)
	FilePath = Column(String, nullable=False)
	InstanceNumber = Column(Integer, nullable=True)
	AcquisitionDateTime = Column(String, nullable=True)

	series: relationship = relationship("Series", back_populates="files")


class DatabaseHandler:
	"""
	Manages database operations using SQLAlchemy ORM.
	"""

	def __init__(self, db_path: Path) -> None:
		"""
		Initialize the DatabaseHandler with an SQLite database.

		Parameters
		----------
		db_path : Path
			Path to the SQLite database file.
		"""
		self.engine = create_engine(f'sqlite:///{db_path}')
		Base.metadata.create_all(self.engine)  # Create tables
		self.Session = sessionmaker(bind=self.engine)

	def get_session(self) -> Session:
		"""
		Create a new SQLAlchemy session.

		Returns
		-------
		Session
			A SQLAlchemy session object.
		"""
		return self.Session()

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

	def build_index_from_files(self, files: List[Path]) -> None:
		"""
		Build an index of DICOM files and insert metadata into the database.

		Parameters
		----------
		files : List[Path]
			List of file paths to index.
		"""
		session = self.db_handler.get_session()
		mytags = [
			'PatientID', 
			'StudyInstanceUID',
			'SeriesInstanceUID',
			'Modality',
			'SOPInstanceUID',
			'StudyDate',
			'StudyDescription',
			'SeriesDescription',
			'InstanceNumber',
			'AccessionNumber',
		]
		for file_path in tqdm.tqdm(files, desc="Indexing DICOM files"):
			metadata = read_tags(file_path, mytags, truncate=False, sanitize=False)

			# Insert Patient
			patient = session.query(Patient).filter_by(PatientID=metadata['PatientID']).first()
			if not patient:
				patient = Patient(PatientID=metadata['PatientID'])
				session.add(patient)

			# Insert Study
			study = session.query(Study).filter_by(StudyInstanceUID=metadata['StudyInstanceUID']).first()
			if not study:
				study = Study(
					StudyInstanceUID=metadata['StudyInstanceUID'],
					PatientID=metadata['PatientID']
				)
				session.add(study)

			# Insert Series
			series = session.query(Series).filter_by(SeriesInstanceUID=metadata['SeriesInstanceUID']).first()
			if not series:
				series = Series(
					SeriesInstanceUID=metadata['SeriesInstanceUID'],
					StudyInstanceUID=metadata['StudyInstanceUID'],
					Modality=metadata['Modality']
				)
				session.add(series)

			# Insert File
			file = session.query(File).filter_by(SOPInstanceUID=metadata['SOPInstanceUID']).first()
			if not file:
				file = File(
					SOPInstanceUID=metadata['SOPInstanceUID'],
					SeriesInstanceUID=metadata['SeriesInstanceUID'],
					FilePath=str(file_path)
				)
				session.add(file)

		session.commit()
		session.close()

class DICOMDatabase:
	"""
	Provides an interface to interact with the DICOM database.
	"""

	def __init__(self, db_handler: DatabaseHandler) -> None:
		"""
		Initialize the DICOMDatabase.

		Parameters
		----------
		db_handler : DatabaseHandler
			An instance of DatabaseHandler for managing database operations.
		"""
		self.db_handler = db_handler

	def get_patients(self) -> List[Patient]:
		"""
		Retrieve all patients from the database.

		Returns
		-------
		List[Patient]
			A list of Patient instances.
		"""
		with self.db_handler.get_session() as session:
			return session.query(Patient).all()

	def get_studies(self) -> List[Study]:
		"""
		Retrieve all studies from the database.

		Returns
		-------
		List[Study]
			A list of Study instances.
		"""
		with self.db_handler.get_session() as session:
			return session.query(Study).all()

	def get_series(self) -> List[Series]:
		"""
		Retrieve all series from the database.

		Returns
		-------
		List[Series]
			A list of Series instances.
		"""
		with self.db_handler.get_session() as session:
			return session.query(Series).all()

	def get_files(self) -> List[File]:
		"""
		Retrieve all files from the database.

		Returns
		-------
		List[File]
			A list of File instances.
		"""
		with self.db_handler.get_session() as session:
			return session.query(File).all()

# def main() -> None:
# 	db_path = Path('dicom_index.sqlite')
# 	db_handler = DatabaseHandler(db_path=db_path)

# 	indexer = DICOMIndexer(db_handler=db_handler)

# 	# Example: Process DICOM files
# 	directory = Path("/Users/bhklab/dev/radiomics/med-imagetools/data/nbia/images/unzipped")
# 	dicom_files = [file for file in directory.rglob("*.dcm")]

# 	logger.info(f"Found {len(dicom_files)} DICOM files.")

# 	# Build index
# 	indexer.build_index_from_files(dicom_files)

# 	# Query the database
# 	dicom_db = DICOMDatabase(db_handler=db_handler)

# 	# Example usage of DICOMDatabase
# 	patients = dicom_db.get_patients()
# 	logger.info(f"Patients: {[p.PatientID for p in patients]}")

# 	# Extract all the info for each file and make it a single row in a dataframe
# 	query = session.query(
# 		File.SOPInstanceUID,
# 		File.FilePath,
# 		File.InstanceNumber,
# 		File.AcquisitionDateTime,
# 		Series.SeriesInstanceUID,
# 		Series.Modality,
# 		Series.Description.label('SeriesDescription'),
# 		Study.StudyInstanceUID,
# 		Study.StudyDate,
# 		Study.Description.label('StudyDescription'),
# 		Patient.PatientID,
# 		Patient.PatientName,
# 		Patient.DOB
# 	).join(Series, File.SeriesInstanceUID == Series.SeriesInstanceUID)\
# 	 .join(Study, Series.StudyInstanceUID == Study.StudyInstanceUID)\
# 	 .join(Patient, Study.PatientID == Patient.PatientID)

# 	df = pd.read_sql(query.statement, session.bind)

# 	# Save the dataframe to a CSV file
# 	output_csv_path = Path('dicom_metadata.csv')
# 	df.to_csv(output_csv_path, index=False)

# 	logger.info(f"Metadata saved to {output_csv_path}")

# 	session.close()


# if __name__ == "__main__":
# 	main()