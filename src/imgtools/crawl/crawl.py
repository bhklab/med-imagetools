import os
import pathlib
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, field
from typing import Dict, List

import pydicom
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from imgtools.crawl.find_dicoms import find_dicoms
from imgtools.logging import logger, logging


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


def crawl_directory(
	top: pathlib.Path,
	extension: str = 'dcm',
	case_sensitive: bool = False,
	recursive: bool = True,
	check_header: bool = False,
	n_jobs: int = -1,
) -> List:
	import time

	start = time.time()

	try:
		dcms = find_dicoms(
			directory=top,
			case_sensitive=case_sensitive,
			recursive=recursive,
			check_header=check_header,
			extension=extension,
		)
	except Exception as e:
		logger.exception(
			'Error finding DICOM files',
			exception=e,
			directory=top,
			case_sensitive=case_sensitive,
			recursive=recursive,
			check_header=check_header,
			extension=extension,
		)
		sys.exit(1)

	logger.info(f'Found {len(dcms)} DICOM files in {time.time() - start:.2f} seconds')

	database_list = []
	num_workers = n_jobs if n_jobs > 0 else os.cpu_count()

	logger.info(
		f'Using {num_workers} workers for parallel processing',
		param_n_jobs=n_jobs,
		os_cpu_count=os.cpu_count(),
	)

	with (
		ProcessPoolExecutor(num_workers) as executor,
		logging_redirect_tqdm([logging.getLogger('imgtools')]),
		tqdm(total=len(dcms), desc='Processing DICOM files') as pbar,
	):
		for database, dcm_path in executor.map(parse_dicom, dcms):
			database_list.append(
				{
					**database,
					'path': dcm_path.relative_to(top).as_posix(),
				},
			)

			pbar.update(1)

	return database_list
