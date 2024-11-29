from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import registry, relationship

if TYPE_CHECKING:
	from pathlib import Path

mapper_registry = registry()

def repr_mixin(cls):
	"""
	A decorator to add a customizable __repr__ method to SQLAlchemy ORM models.

	Includes scalar fields (e.g., columns) and prints the length of lists for relationships.
	"""
	def __repr__(self):
		# Fetch attributes and handle lists separately
		attrs = {
			key: (len(value) if isinstance(value, list) else value)
			for key, value in vars(self).items()
			if not key.startswith("_") and isinstance(value, (str, int, float, list))
		}
		class_name = self.__class__.__name__
		fields = ",\n  ".join(f"{key}={value}" for key, value in attrs.items())
		return f"<{class_name}(\n  {fields}\n)>"
	cls.__repr__ = __repr__
	return cls

# Patient Table
@repr_mixin
@mapper_registry.mapped
@dataclass
class Patient:
		__table__ = Table(
				"patients",
				mapper_registry.metadata,
				Column("PatientID", String, primary_key=True, index=True), # PRIMARY KEY
		)

		# Metadata from DICOM
		PatientID: str = field(init=True)

		# Relationships
		studies: List[Study] = field(default_factory=list)

		__mapper_args__ = {  # type: ignore
				"properties": {
						"studies": relationship("Study", back_populates="patient"),
				}
		}

		@classmethod
		def from_metadata(cls, metadata: Dict[str, str]) -> Patient:
				"""
				Create a Patient instance from metadata.

				Parameters
				----------
				metadata : Dict[str, Optional[str]]
						Patient metadata.

				Returns
				-------
				Patient
						A Patient instance.
				"""
				return cls(
						PatientID=metadata["PatientID"],
				)

		@property
		def num_studies(self) -> int:
				"""
				Get the number of studies for the patient.

				Returns
				-------
				int
						The number of studies.
				"""
				return len(self.studies)

		@property
		def num_series(self) -> int:
				"""
				Get the number of series for the patient.

				Returns
				-------
				int
						The number of series.
				"""
				return sum(len(study.series) for study in self.studies)

		@property
		def modalities(self) -> Dict[str, int]:
				"""
				Get the list of modalities for the patient.

				Returns
				-------
				List[str]
						The list of modalities.
				"""
				modalities = [modality for study in self.studies for modality in study.modalities]
				return dict(Counter(modalities))


# Study Table
@repr_mixin
@mapper_registry.mapped
@dataclass
class Study:
		__table__ = Table(
				"studies",
				mapper_registry.metadata,
				Column("StudyInstanceUID", String, primary_key=True), # PRIMARY KEY
				Column("PatientID", String, ForeignKey("patients.PatientID"), nullable=False),

		)

		# Metadata from DICOM
		StudyInstanceUID: str = field(init=True)  # PRIMARY KEY
		PatientID: str = field(init=True) # FOREIGN KEY

		# Relationships
		patient: Patient = field(init=False)
		series: List[Series] = field(default_factory=list)

		__mapper_args__ = {  # type: ignore
				"properties": {
						"patient": relationship("Patient", back_populates="studies"),
						"series": relationship("Series", back_populates="study"),
				}
		}

		@classmethod
		def from_metadata(cls, metadata: Dict[str, str]) -> Study:
				"""
				Create a Study instance from metadata.

				Parameters
				----------
				metadata : Dict[str, Optional[str]]
						Study metadata.

				Returns
				-------
				Study
						A Study instance.
				"""
				return cls(
						StudyInstanceUID=metadata["StudyInstanceUID"],
						PatientID=metadata["PatientID"],
				)

		@property
		def num_files(self) -> int:
				"""
				Get the number of files in the study.

				Returns
				-------
				int
						The number of files.
				"""
				return sum(series.num_files for series in self.series)

		@property
		def modalities(self) -> Dict[str, int]:
				"""
				Get the list of modalities in the study.

				Returns
				-------
				List[str]
						The list of modalities.
				"""

				modalities = [series.Modality for series in self.series]
				return dict(Counter(modalities))

		@property
		def unique_modalities(self) -> List[str]:
				"""
				Get the unique modalities in the study.

				Returns
				-------
				List[str]
						The unique modalities.
				"""
				return list(self.modalities.keys())

# Series Table
@repr_mixin
@mapper_registry.mapped
@dataclass
class Series:
		__table__ = Table(
				"series",
				mapper_registry.metadata,
				Column("SeriesInstanceUID", String, primary_key=True), # PRIMARY KEY
				Column("StudyInstanceUID", String, ForeignKey("studies.StudyInstanceUID"), nullable=False),
				Column("Modality", String, nullable=False),
		)

		# Metadata from DICOM
		SeriesInstanceUID: str = field(init=True)  # PRIMARY KEY
		StudyInstanceUID: str = field(init=True) # FOREIGN KEY
		Modality: str = field(init=True)

		# Relationships
		study: Study = field(init=False) 
		files: List[File] = field(default_factory=list)

		__mapper_args__ = {  # type: ignore
				"properties": {
						"study": relationship("Study", back_populates="series"),
						"files": relationship("File", back_populates="series"),
				}
		}

		@classmethod
		def from_metadata(cls, metadata: Dict[str, str]) -> Series:
				"""
				Create a Series instance from metadata.

				Parameters
				----------
				metadata : Dict[str, Optional[str]]
						Series metadata.

				Returns
				-------
				Series
						A Series instance.
				"""
				return cls(
						SeriesInstanceUID=metadata["SeriesInstanceUID"],
						StudyInstanceUID=metadata["StudyInstanceUID"],
						Modality=metadata["Modality"],
				)

		@property
		def num_files(self) -> int:
				"""
				Get the number of files in the series.

				Returns
				-------
				int
						The number of files.
				"""
				return len(self.files)

# File Table
@repr_mixin
@mapper_registry.mapped
@dataclass
class File:
		__table__ = Table(
				"files",
				mapper_registry.metadata,
				Column("FilePath", String, primary_key=True), # PRIMARY KEY
				Column("SOPInstanceUID", String, nullable=False),
				Column("SeriesInstanceUID", String, ForeignKey("series.SeriesInstanceUID"), nullable=False),
		)

		# Metadata from DICOM
		FilePath: str = field(init=True)
		SOPInstanceUID: str = field(init=True)
		SeriesInstanceUID: str = field(init=True)

		# Relationships
		series: Series = field(init=False)

		__mapper_args__ = {  # type: ignore
				"properties": {
						"series": relationship("Series", back_populates="files"),
				}
		}
	
		@classmethod
		def from_metadata(cls, metadata: Dict[str, str], file_path: Path) -> File:
				"""
				Create a File instance from metadata.

				Parameters
				----------
				metadata : Dict[str, Optional[str]]
						File metadata.

				Returns
				-------
				File
						A File instance.
				"""
				return cls(
						SOPInstanceUID=metadata["SOPInstanceUID"],
						SeriesInstanceUID=metadata["SeriesInstanceUID"],
						FilePath=file_path.as_posix()
				)

