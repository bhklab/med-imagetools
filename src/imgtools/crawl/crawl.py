from dataclasses import asdict, dataclass, field
import sys
import os
import pathlib
from typing import Dict
from pydicom import dcmread
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from imgtools.logging import logger, logging
from concurrent.futures import ProcessPoolExecutor


def get_first(meta, attribute_name):
    try:
        return getattr(meta, attribute_name)[0]
    except:
        return ""


def get_str(meta, attribute_name):
    if attribute_name == "reference":
        return asdict(get_reference(meta))
    return str(getattr(meta, attribute_name, ""))


@dataclass
class ReferenceInfo:
    reference_ct: str = field(default="")
    reference_rs: str = field(default="")
    reference_pl: str = field(default="")


def get_reference(meta):
    if meta.Modality == "CT":
        return ReferenceInfo()
    elif meta.Modality == "RTSTRUCT":
        return ReferenceInfo(
            reference_ct=meta.ReferencedFrameOfReferenceSequence[0]
            .RTReferencedStudySequence[0]
            .RTReferencedSeriesSequence[0]
            .SeriesInstanceUID
        )
    elif meta.Modality == "RTDOSE":
        return ReferenceInfo(
            reference_rs=get_str(
                getattr(meta, "ReferencedStructureSetSequence")[0],
                "ReferencedSOPInstanceUID",
            ),
            reference_ct=get_str(
                getattr(meta, "ReferencedImageSequence")[0],
                "ReferencedSOPInstanceUID",
            ),
            reference_pl=get_str(
                getattr(meta, "ReferencedRTPlanSequence")[0],
                "ReferencedSOPInstanceUID",
            ),
        )
    elif meta.Modality == "SEG":
        return ReferenceInfo(
            reference_ct=meta.ReferencedSeriesSequence[0].SeriesInstanceUID
        )
    else:
        return ReferenceInfo()

def parse_dicom(dcm_path: pathlib.Path) -> Dict[str, str]:
    desired_attributes = [
        "PatientID",
        "StudyInstanceUID",
        "SeriesInstanceUID",
        "Modality",
        "SOPInstanceUID",
        "AcquisitionNumber",
        "InstanceNumber",
        "ImageOrientationPatient",
        "AnatomicalOrientationType",
        "reference",
    ]
    meta = dcmread(dcm_path, force=True, stop_before_pixels=True)
    try:
        return {attr: get_str(meta, attr) for attr in desired_attributes}, dcm_path
    except Exception as e:
        logger.exception(
            "Error processing file", exception=e, path=dcm_path, modality=meta.Modality
        )
        sys.exit(1)


def crawl_directory(top: pathlib.Path, n_jobs: int = -1) -> list:
    # top is the input directory in the argument parser from autotest.py
    dcms = [file for file in pathlib.Path(top).rglob("*.dcm") if file.is_file()]
    logger.info(f"Found {len(dcms)} DICOM files in {top}")
    database_list = []
    with ProcessPoolExecutor(n_jobs if n_jobs > 0 else os.cpu_count()) as executor:
        with logging_redirect_tqdm([logging.getLogger("imgtools")]):
            with tqdm(total=len(dcms), desc="Processing DICOM files") as pbar:
                for database, dcm_path in executor.map(parse_dicom, dcms):
                    database_list.append(
                        {
                            **database,
                            "path": dcm_path.relative_to(top).as_posix(),
                        }
                    )

                    pbar.update(1)

    return database_list
