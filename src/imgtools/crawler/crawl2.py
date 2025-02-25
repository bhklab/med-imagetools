import logging
import pathlib
import time
import typing as t
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from functools import partial

import click
from pydicom import dcmread
from pydicom.errors import InvalidDicomError
from rich import print as rprint
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from imgtools.dicom.input import rtstruct_reference_uids
from imgtools.dicom import find_dicoms
from imgtools.logging import logger

TAGS_OF_INTEREST = [
    "PatientID",
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "SOPInstanceUID",
    "Modality",
]


def parse_dicom(dcm_path: pathlib.Path, top: pathlib.Path) -> t.Dict:
    try:
        dcm = dcmread(
            dcm_path,
            force=True,
            stop_before_pixels=True,
        )
    except InvalidDicomError as e:
        logger.error(f"Error reading {dcm_path}: {e}")
        raise

    meta = {tag: str(dcm.get(tag, "")) for tag in TAGS_OF_INTEREST}

    match meta["Modality"]:
        case "RTSTRUCT":
            refseries, refstudy = rtstruct_reference_uids(dcm)
            meta["ReferencedSeriesUID"] = refseries
        case "RTPLAN":
            meta["ReferencedRTStructInstanceUID"] = (
                dcm.ReferencedStructureSetSequence[0].ReferencedSOPInstanceUID
            )
        case "RTDOSE":
            meta["ReferencedRTPlanInstanceUID"] = dcm.ReferencedRTPlanSequence[
                0
            ].ReferencedSOPInstanceUID
        case "SEG":
            try:
                meta["ReferencedSeriesUID"] = dcm.ReferencedSeriesSequence[
                    0
                ].SeriesInstanceUID
            except AttributeError:
                # No referenced series i.e ISPY2
                # get the first referenced instance
                # hope that we can find the series from that
                meta["ReferencedSOPInstanceUID"] = dcm.SourceImageSequence[
                    0
                ].ReferencedSOPInstanceUID
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

    dcms = find_dicoms(
        directory=top,
        recursive=recursive,
        check_header=check_header,
        extension=extension,
    )

    logger.info(
        f"Found {len(dcms)} DICOM files in {time.time() - start:.2f} seconds"
    )

    database_list = []

    logger.info(
        f"Using {n_jobs} workers for parallel processing",
        param_n_jobs=n_jobs,
    )
    start = time.time()

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
    logger.info(f"Total time: {time.time() - start:.2f} seconds")

    logger.info(
        f"Database: {len(database_list)} out of {len(dcms)} DICOM files in {time.time() - start:.2f} seconds"
    )
    # Combine all the JSON files into one
    logger.info("Combining JSON files...")

    start = time.time()
    grouped = defaultdict(list)
    for item in database_list:
        grouped[item["SeriesInstanceUID"]].append(item)

    logger.info(f"Grouping took {time.time() - start:.2f} seconds")

    return grouped


@click.command()
@click.argument("top", type=click.Path(exists=True))
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

    crawl_directory(
        top=top_dir,
        extension=extension,
        recursive=not no_recursive,
        check_header=check_header,
        n_jobs=n,
    )


if __name__ == "__main__":
    # main()
    all_start = time.time()
    x = crawl_directory(
        pathlib.Path("./data").resolve(),
        extension="dcm",
        recursive=True,
        n_jobs=12,
    )

    keys = list(x.keys())

    # Group by Modality
    modality_group = defaultdict(list)
    for key in keys:
        modality = x[key][0]["Modality"]
        match modality:
            case "RTSTRUCT" | "RTPLAN" | "RTDOSE" | "SEG":
                # should only be one instance
                modality_group[modality].append(x[key][0])
            case _:
                modality_group[modality].extend(x[key])

    # create a hashmap of
    # sop_instance_uid -> series_instance_uid
    
    sop_to_series_map = {}
    for series_uid, items in x.items():
        for item in items:
            sop_instance_uid = item["SOPInstanceUID"]
            sop_to_series_map[sop_instance_uid] = series_uid

    start = time.time()
    for instance in tqdm(
        modality_group["RTPLAN"], desc="Mapping RTPLAN instances"
    ):
        instance["ReferencedSeriesUID"] = sop_to_series_map[
            instance["ReferencedRTStructInstanceUID"]
        ]

    for instance in tqdm(
        modality_group["RTDOSE"], desc="Mapping RTDOSE instances"
    ):
        instance["ReferencedSeriesUID"] = sop_to_series_map[
            instance["ReferencedRTPlanInstanceUID"]
        ]

    for instance in tqdm(modality_group["SEG"], desc="Mapping   SEG instances"):
        if "ReferencedSOPInstanceUID" in instance:
            if instance["ReferencedSOPInstanceUID"] in sop_to_series_map:
                instance["ReferencedSeriesUID"] = sop_to_series_map[
                    instance["ReferencedSOPInstanceUID"]
                ]
            else:
                errmsg = f"Could not find {instance['meta']['ReferencedSOPInstanceUID']=} in mapping"
                raise ValueError(errmsg)
        elif "ReferencedSeriesUID" in instance:
            assert instance["ReferencedSeriesUID"] in x
        else:
            errmsg = "Something went wrong"
            raise ValueError(errmsg)

    rprint(f"Remapping instances took {time.time() - start:.2f} seconds")
    new_series_dicts = []

    for series_uid, instances in x.items():
        modality = instances[0]["Modality"]
        patient = instances[0]["PatientID"]
        study = instances[0]["StudyInstanceUID"]

        ref_series = instances[0].get("ReferencedSeriesUID", None)

        new_series_dicts.append(
            {
                "PatientID": patient,
                "StudyInstanceUID": study,
                "SeriesInstanceUID": series_uid,
                "Modality": modality,
                "ReferencedSeriesUID": ref_series,
            }
        )
    
    rprint(f"Total time: {time.time() - all_start:.2f} seconds")
    # import json

    # with pathlib.Path("series_crawl.json").open("w") as f:
    #     json.dump(new_series_dicts, f, indent=4)

    # import pandas as pd

    # df = pd.DataFrame(new_series_dicts)

    # df.to_csv("series_crawl.csv", index=False)


# print(list(sop_to_series_map.items())[:5])

# for series_instances in x.items():
#     match series_instances:
#         case (series_uid, [single_instance]):
#             print(
#                 f"Series: {series_uid} : {single_instance['meta']['Modality']}"
#             )
#         case (series_uid, list(instances)) if (instances[0]['meta']['Modality'] in ['CT', 'MR']):
#             continue
#         case (series_uid, [*instances]):
#             print(
#                 f"Series: {series_uid} : {instances[0]['meta']['Modality']} {len(instances)} instances"
#             )
#         case _:
#             pass
