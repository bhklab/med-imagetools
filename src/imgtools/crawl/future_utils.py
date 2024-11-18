"""
Playground of the refactor of crawl.py
"""

import pathlib
import sys
from dataclasses import asdict, dataclass, field
from typing import Dict

import pydicom

from imgtools.logging import logger


def get_first(meta, attribute_name):  # noqa: ANN001, ANN201
	try:
		return getattr(meta, attribute_name)[0]
	except:
		return ''


def get_str(meta, attribute_name):  # noqa: ANN001, ANN201
	if attribute_name == 'reference':
		return asdict(get_reference(meta))
	return str(getattr(meta, attribute_name, ''))


@dataclass
class ReferenceInfo:
	reference_ct: str = field(default='')
	reference_rs: str = field(default='')
	reference_pl: str = field(default='')


def get_reference(meta: pydicom.dataset.FileDataset) -> ReferenceInfo:
	if meta.Modality == 'CT':
		return ReferenceInfo()
	elif meta.Modality == 'RTSTRUCT':
		return ReferenceInfo(
			reference_ct=meta.ReferencedFrameOfReferenceSequence[0]
			.RTReferencedStudySequence[0]
			.RTReferencedSeriesSequence[0]
			.SeriesInstanceUID,
		)
	elif meta.Modality == 'RTDOSE':
		return ReferenceInfo(
			reference_rs=get_str(meta, 'ReferencedStructureSetSequence'),
			reference_ct=get_str(meta, 'ReferencedImageSequence'),
			reference_pl=get_str(meta, 'ReferencedRTPlanSequence'),
		)
	elif meta.Modality == 'SEG':
		return ReferenceInfo(
			reference_ct=meta.ReferencedSeriesSequence[0].SeriesInstanceUID,
		)
	else:
		return ReferenceInfo()


def parse_dicom(dcm_path: pathlib.Path) -> Dict[str, str]:
	desired_attributes = [
		'PatientID',
		'StudyInstanceUID',
		'SeriesInstanceUID',
		'Modality',
		'SOPInstanceUID',
		'AcquisitionNumber',
		'InstanceNumber',
		'ImageOrientationPatient',
		'AnatomicalOrientationType',
		'reference',
	]
	meta = pydicom.dcmread(dcm_path, force=True, stop_before_pixels=True)
	try:
		return {attr: get_str(meta, attr) for attr in desired_attributes}, dcm_path
	except Exception as e:
		logger.exception(
			'Error processing file',
			exception=e,
			path=dcm_path,
			modality=meta.Modality,
		)
		sys.exit(1)
