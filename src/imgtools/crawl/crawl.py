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
            reference_rs=get_str(meta, "ReferencedStructureSetSequence"),
            reference_ct=get_str(meta, "ReferencedImageSequence"),
            reference_pl=get_str(meta, "ReferencedRTPlanSequence"),
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


def crawl_directory(
    top: pathlib.Path,
    extension: str = "dcm",
    case_sensitive: bool = False,
    n_jobs: int = -1,
) -> list:
    # top is the input directory in the argument parser from autotest.py
    logger.info(
        "Lookging for DICOM files",
        top=top,
        search_extension=extension,
        case_sensitive=case_sensitive,
    )

    dcms = [
        file
        for file in top.rglob(f"*.{extension}", case_sensitive=case_sensitive)
        if file.is_file()
    ]
    logger.info(f"Found {len(dcms)} DICOM files")

    database_list = []
    N_WORKERS = n_jobs if n_jobs > 0 else os.cpu_count()

    logger.info(
        f"Using {N_WORKERS} workers for parallel processing",
        param_n_jobs=n_jobs,
        os_cpu_count=os.cpu_count(),
    )

    with (
        ProcessPoolExecutor(N_WORKERS) as executor,
        logging_redirect_tqdm([logging.getLogger("imgtools")]),
        tqdm(total=len(dcms), desc="Processing DICOM files") as pbar,
    ):
        for database, dcm_path in executor.map(parse_dicom, dcms):
            database_list.append(
                {
                    **database,
                    "path": dcm_path.relative_to(top).as_posix(),
                }
            )

            pbar.update(1)

    return database_list