import logging
import pathlib
import time
import typing as t
from collections import defaultdict
from concurrent.futures import (
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    as_completed,
)
from functools import partial

import click
from joblib import Parallel, delayed
from pydicom import dcmread
from pydicom.errors import InvalidDicomError
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from imgtools.dicom import find_dicoms
from imgtools.dicom.input import rtstruct_reference_uids
from imgtools.logging import logger

TAGS_OF_INTEREST = [
    "PatientID",
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "SOPInstanceUID",
    "Modality",
]


# A lightweight subclass of dict that allows for attribute access
class AttrDict(dict):
    def __getattr__(self, key: str) -> str | list:
        return self[key]

    def __setattr__(self, key: str, value: str | list) -> None:
        self[key] = value


def parse_dicom(dcm_path: str) -> t.Dict:
    try:
        dcm = dcmread(
            dcm_path,
            force=True,
            stop_before_pixels=True,
        )
    except InvalidDicomError as e:
        logger.error(f"Error reading {dcm_path}: {e}")
        raise

    meta = AttrDict({tag: str(dcm.get(tag)) for tag in TAGS_OF_INTEREST})
    meta.filepath = dcm_path
    match meta["Modality"]:
        case "SEG":
            try:
                ref_series = dcm.ReferencedSeriesSequence[0].SeriesInstanceUID
                meta.ReferencedSeriesUID = ref_series
            except AttributeError:
                ref_seg_instance = dcm.SourceImageSequence[
                    0
                ].ReferencedSOPInstanceUID
                meta.ReferencedSOPInstanceUID = ref_seg_instance
        case "RTSTRUCT":
            ref_series, refstudy = rtstruct_reference_uids(dcm)
            meta.ReferencedSeriesUID = ref_series
        case "RTPLAN":
            ref_struct = dcm.ReferencedStructureSetSequence[
                0
            ].ReferencedSOPInstanceUID
            meta.ReferencedRTStructInstanceUID = ref_struct
        case "RTDOSE":
            ref_plan = dcm.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID
            meta.ReferencedRTPlanInstanceUID = ref_plan
        case "SR":
            if sr_seq := getattr(
                dcm, "CurrentRequestedProcedureEvidenceSequence", None
            ):
                ref_series = {
                    sr.ReferencedSeriesSequence[0].SeriesInstanceUID
                    for sr in sr_seq
                }
                meta.ReferencedSeriesUID = list(ref_series)
        case _:
            pass

    return meta


def crawl_directory(
    top: pathlib.Path,
    extension: str = "dcm",
    recursive: bool = True,
    check_header: bool = False,
    n_jobs: int = -1,
) -> t.Dict:
    start = time.time()

    dcms_p: t.List[pathlib.Path] = find_dicoms(
        directory=top,
        recursive=recursive,
        check_header=check_header,
        extension=extension,
        search_input=["SR"],
    )
    dcms = [dcm.as_posix() for dcm in dcms_p]

    logger.info(
        f"Found {len(dcms)} DICOM files in {time.time() - start:.2f} seconds"
    )

    logger.info(
        f"Using {n_jobs} workers for parallel processing with",
        param_n_jobs=n_jobs,
    )
    start = time.time()
    grouped = defaultdict(list)

    # this seems to be faster than using ProcessPoolExecutor
    with logging_redirect_tqdm([logging.getLogger("imgtools")]):
        result = Parallel(n_jobs=n_jobs)(
            delayed(parse_dicom)(dcm)
            for dcm in tqdm(dcms, desc="Processing DICOM files", mininterval=1)
        )
        for res in result:
            if res:
                grouped[res["SeriesInstanceUID"]].append(res)

    logger.info(f"Total time: {time.time() - start:.2f} seconds")
    return grouped


@click.command()
@click.argument("top", type=click.Path(exists=True, path_type=pathlib.Path))
@click.option(
    "--extension", default="dcm", help="File extension to search for"
)
@click.option(
    "--no-recursive", is_flag=True, help="Recursively search directories"
)
@click.option("--check-header", is_flag=True, help="Check header for DICOM")
@click.option("-n", default=1, help="Number of parallel jobs")
def main(
    top: str,
    extension: str,
    no_recursive: bool,
    check_header: bool,
    n: int,
) -> None:
    top_dir = pathlib.Path(top).resolve()

    result = crawl_directory(
        top=top_dir,
        extension=extension,
        recursive=not no_recursive,
        check_header=check_header,
        n_jobs=n,
    )
    import json
    from pprint import pprint as pp
    # print(json.dumps(result, indent=4))

    # get all the series where the "ReferencedSeriesUID" is a list of more than 1
    for series, metas in result.items():
        for meta in metas:
            if len(meta.get("ReferencedSeriesUID", [])) > 1:
                print(f"Series: {series}")
                pp(meta.get("ReferencedSeriesUID"))
                print()


if __name__ == "__main__":
    main()
