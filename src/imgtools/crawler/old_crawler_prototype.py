import pathlib
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextlib import suppress
from functools import partial
from typing import Dict, List

from pydicom import dcmread
from pydicom.dataset import Dataset
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from imgtools.dicom.utils import find_dicoms
from imgtools.logging import logger, logging


def _deep_merge(base: dict, new: dict) -> dict:
    for key, value in new.items():
        if isinstance(value, dict) and key in base:
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _combine_jsons(json_list: List[Dict]) -> dict:
    result = defaultdict(dict)
    for json_obj in json_list:
        for key, value in json_obj.items():
            if key == "path":  # TODO: remove this
                # Skip paths; if needed, integrate here.
                continue
            result[key] = _deep_merge(result[key], value)
    return dict(result)


def _get_meta_attribute(
    meta: Dataset, attribute: str, cast_type: type = str, default: str = ""
) -> str:
    with suppress(Exception):
        return cast_type(getattr(meta, attribute))
    return default


def _get_references(meta: Dataset) -> tuple:
    # TODO: Update this to match the old crawl logic
    reference_ct, reference_rs, reference_pl = "", "", ""
    try:
        reference_ct = str(
            meta.ReferencedFrameOfReferenceSequence[0]
            .RTReferencedStudySequence[0]
            .RTReferencedSeriesSequence[0]
            .SeriesInstanceUID
        )
    except:
        with suppress(Exception):
            reference_ct = str(meta.ReferencedSeriesSequence[0].SeriesInstanceUID)
        with suppress(Exception):
            reference_rs = str(
                meta.ReferencedStructureSetSequence[0].ReferencedSOPInstanceUID
            )
        with suppress(Exception):
            reference_ct = str(meta.ReferencedImageSequence[0].ReferencedSOPInstanceUID)
        with suppress(Exception):
            reference_pl = str(
                meta.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID
            )
    return reference_ct, reference_rs, reference_pl


def _get_reference_frame(meta: Dataset) -> str:
    with suppress(Exception):
        return str(meta.FrameOfReferenceUID)
    with suppress(Exception):
        # only rtstruct has this
        return str(meta.ReferencedFrameOfReferenceSequence[0].FrameOfReferenceUID)
    return ""


def parse_dicom(dcm_path: pathlib.Path, top: pathlib.Path) -> Dict[str, str]:
    try:
        meta = dcmread(dcm_path, force=True, stop_before_pixels=True)

        try:
            patient = str(meta.PatientID)
            study = str(meta.StudyInstanceUID)
            series = str(meta.SeriesInstanceUID)
            instance = str(meta.SOPInstanceUID)
        except Exception as e:
            logger.exception(
                "Error parsing DICOM", exc_info=e, extra={"path": dcm_path}
            )
            raise e
        orientation = _get_meta_attribute(meta, "ImageOrientationPatient")
        orientation_type = _get_meta_attribute(meta, "AnatomicalOrientationType")

        tr, te, tesla, scan_seq, elem = "", "", "", "", ""

        reference_ct, reference_rs, reference_pl = _get_references(meta)

        tr = _get_meta_attribute(meta, "RepetitionTime", float)
        te = _get_meta_attribute(meta, "EchoTime", float)
        scan_seq = _get_meta_attribute(meta, "ScanningSequence")
        tesla = _get_meta_attribute(meta, "MagneticFieldStrength", float)
        elem = _get_meta_attribute(meta, "ImagedNucleus")

        reference_frame = _get_reference_frame(meta)
        study_description = _get_meta_attribute(meta, "StudyDescription")
        series_description = _get_meta_attribute(meta, "SeriesDescription")
        subseries = _get_meta_attribute(meta, "AcquisitionNumber", default="default")

        return {
            patient: {
                study: {
                    "study_description": study_description,
                    series: {
                        "series_description": series_description,
                        subseries: {
                            "instances": {
                                instance: dcm_path.relative_to(top).as_posix()
                            },
                            "instance_uid": instance,
                            "modality": meta.Modality,
                            "reference_ct": reference_ct,
                            "reference_rs": reference_rs,
                            "reference_pl": reference_pl,
                            "reference_frame": reference_frame,
                            "folder": dcm_path.parent.relative_to(top).as_posix(),
                            "orientation": orientation,
                            "orientation_type": orientation_type,
                            "repetition_time": tr,
                            "echo_time": te,
                            "scan_sequence": scan_seq,
                            "mag_field_strength": tesla,
                            "imaged_nucleus": elem,
                        },
                    },
                }
            }
        }

    except Exception as e:
        logger.exception("Error processing file", exc_info=e, extra={"path": dcm_path})


def crawl_directory(
    top: pathlib.Path,
    extension: str = "dcm",
    case_sensitive: bool = False,
    recursive: bool = True,
    check_header: bool = False,
    n_jobs: int = -1,
) -> Dict:
    start = time.time()

    dcms = find_dicoms(
        directory=top,
        case_sensitive=case_sensitive,
        recursive=recursive,
        check_header=check_header,
        extension=extension,
    )

    logger.info(f"Found {len(dcms)} DICOM files in {time.time() - start:.2f} seconds")

    database_list = []

    logger.info(
        f"Using {n_jobs} workers for parallel processing",
        param_n_jobs=n_jobs,
    )

    parse_dicom_partial = partial(parse_dicom, top=top)
    start = time.time()
    with (
        ProcessPoolExecutor(n_jobs) as executor,
        logging_redirect_tqdm([logging.getLogger("imgtools")]),
        tqdm(total=len(dcms), desc="Processing DICOM files") as pbar,
    ):
        for database in executor.map(parse_dicom_partial, dcms):
            database_list.append(database)

            pbar.update(1)
    logger.info(
        f"Database: {len(database_list)} out of {len(dcms)} DICOM files in {time.time() - start:.2f} seconds"
    )
    # Combine all the JSON files into one
    logger.info("Combining JSON files...")
    db = _combine_jsons(database_list)
    return db
