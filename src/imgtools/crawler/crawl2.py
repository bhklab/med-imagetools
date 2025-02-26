import json
import logging
import os
import pathlib
import time
import typing as t
from collections import defaultdict

import click
import pandas as pd
from joblib import Parallel, delayed  # type: ignore
from pydicom import dcmread
from pydicom.errors import InvalidDicomError
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm  # type: ignore

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
            ref_series, _ = rtstruct_reference_uids(dcm)
            meta.ReferencedSeriesUID = ref_series

        # For RTPLAN and RTDOSE, we store the same id Twice, for debugging, but we will
        # only use the common `ReferencedSOPInstanceUID` (also used in SEG)
        case "RTPLAN":
            ref_struct = dcm.ReferencedStructureSetSequence[
                0
            ].ReferencedSOPInstanceUID
            meta.ReferencedRTStructInstanceUID = ref_struct
            meta.ReferencedSOPInstanceUID = ref_struct
        case "RTDOSE":
            ref_plan = dcm.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID
            meta.ReferencedRTPlanInstanceUID = ref_plan
            meta.ReferencedSOPInstanceUID = ref_plan
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


def extract_compact_data(entries: list, root: pathlib.Path) -> dict:
    """Extracts unique metadata and instance-to-filepath mapping.

    Parameters
    ----------
    data : dict
        The input dictionary containing DICOM metadata.

    Returns
    -------
    dict
        A dictionary with compact metadata and instance-filepath mapping.
    """
    # Extract the first item (since all share common metadata)
    common_metadata = {
        "PatientID": entries[0]["PatientID"],
        "StudyInstanceUID": entries[0]["StudyInstanceUID"],
        "SeriesInstanceUID": entries[0]["SeriesInstanceUID"],
        "Modality": entries[0]["Modality"],
    }
    if "ReferencedSeriesUID" in entries[0]:
        common_metadata["ReferencedSeriesUID"] = entries[0][
            "ReferencedSeriesUID"
        ]
    elif "ReferencedSOPInstanceUID" in entries[0]:
        common_metadata["ReferencedSOPInstanceUID"] = entries[0][
            "ReferencedSOPInstanceUID"
        ]

    instance_files = {
        entry["SOPInstanceUID"]: pathlib.Path(entry["filepath"])
        for entry in entries
    }

    instance_map = {
        uid: filepath.relative_to(root).as_posix()
        for uid, filepath in instance_files.items()
    }

    # we do assume that all instances share a common root
    # but just in case...
    common_root = os.path.commonpath(instance_files.values())

    return {
        **common_metadata,
        "common_root": common_root,
        "instances": instance_map,
    }


def create_sop_to_series_map(metadata: dict) -> dict:
    """Create a mapping of SOPInstanceUID to SeriesInstanceUID.

    Parameters
    ----------
    compact_metadata : dict

    Returns
    -------
    dict
        A dictionary mapping SOPInstanceUID to SeriesInstanceUID.
    """
    sop_to_series_map = {}
    for series_uid, meta in metadata.items():
        for sop_instance_uid in meta["instances"]:  # .keys():
            sop_to_series_map[sop_instance_uid] = series_uid
    return sop_to_series_map


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
) -> t.Dict:
    start = time.time()
    top_dir = pathlib.Path(top).resolve()
    meta_path_cache_file = pathlib.Path(".imgtools/cache/meta_cache.json")
    meta_path_cache_file.parent.mkdir(exist_ok=True)
    if meta_path_cache_file.exists():
        with meta_path_cache_file.open("r") as f:
            metadata = json.load(f)
    else:
        metadata = crawl_directory(
            top=top_dir,
            extension=extension,
            recursive=not no_recursive,
            check_header=check_header,
            n_jobs=n,
        )
        json.dump(metadata, meta_path_cache_file.open("w"), indent=4)

    logger.info("Remapping final metadata")
    meta = {
        series_uid: extract_compact_data(data, top_dir)
        for series_uid, data in metadata.items()
    }
    with pathlib.Path(".imgtools/cache/meta_compact.json").open("w") as f:
        json.dump(meta, f, indent=4)

    sop_to_series_map = create_sop_to_series_map(meta)
    with pathlib.Path(".imgtools/cache/sop_to_series_map.json").open("w") as f:
        json.dump(sop_to_series_map, f, indent=4)

    final_meta = []
    # doing this manually for now
    # refactor would just be make a huge dataframe and then filter columns
    for series_uid, data in meta.items():
        base_meta = {
            "PatientID": data["PatientID"],
            "StudyInstanceUID": data["StudyInstanceUID"],
            "SeriesInstanceUID": series_uid,
            "Modality": data["Modality"],
            "ReferencedSeriesUID": data.get("ReferencedSeriesUID", None),
            "Instances": len(data["instances"]),
        }

        match data["Modality"]:
            case "CT" | "MR" | "PT" | "RTSTRUCT":
                # would've been processed in the first pass
                pass
            case "SEG":
                base_meta["ReferencedSeriesUID"] = data.get(
                    "ReferencedSeriesUID",
                    sop_to_series_map.get(
                        data.get("ReferencedSOPInstanceUID"), None
                    ),
                )
            case "RTPLAN" | "RTDOSE":
                base_meta["ReferencedSeriesUID"] = sop_to_series_map.get(
                    data.get("ReferencedSOPInstanceUID"), None
                )
            case "SR":
                base_meta["ReferencedSeriesUID"] = "|".join(
                    data["ReferencedSeriesUID"]
                )
            case _:
                debugmsg = (
                    f"Modality {data['Modality']} not accounted for in mapping"
                )
                logger.debug(debugmsg)

        if (path := pathlib.Path(data.get("common_root"))).is_file():  # type: ignore
            base_meta["folder"] = path.parent.relative_to(top_dir.parent).as_posix()
            base_meta["file"] = path.relative_to(top_dir.parent).as_posix()
        else:
            base_meta["folder"] = path.relative_to(top_dir.parent).as_posix()

        final_meta.append(base_meta)

    df = pd.DataFrame(final_meta)
    # set the index to the SeriesInstanceUID
    df.set_index("SeriesInstanceUID", inplace=True)

    # create a new column that uses the ReferencedSeriesUID to get the Modality of the referenced series
    # if the ReferencedSeriesUID has a "|" in it, then we have multiple references
    # and we will get both and separate them by "|"
    for row in df.itertuples():
        if pd.notna(row.ReferencedSeriesUID):
            ref_series = str(row.ReferencedSeriesUID).split("|")
            ref_modality = "|".join(
                [
                    str(df.loc[ref, "Modality"])
                    if (pd.notna(ref) and ref in df.index)
                    else ""
                    for ref in ref_series
                ]
            )
            df.at[row.Index, "ReferencedModality"] = ref_modality
        else:
            df.at[row.Index, "ReferencedModality"] = ""

    df.sort_values(
        by=["PatientID", "StudyInstanceUID", "Modality"],
        inplace=True,
    )

    # use normal indexing
    df.reset_index(inplace=True)

    # reorganize columns
    df = df[
        [
            "PatientID",
            "StudyInstanceUID",
            "SeriesInstanceUID",
            "Instances",
            "Modality",
            "ReferencedModality",
            "ReferencedSeriesUID",
            "folder",
            "file",
        ]
    ]

    df.to_csv(".imgtools/cache/final_meta.csv", index=False)
    logger.info(f"Total time: {time.time() - start:.2f} seconds")
    return meta


if __name__ == "__main__":
    main()

    # main(
    #     top="./data",
    #     extension="dcm",
    #     no_recursive=False,
    #     check_header=False,
    #     n=12,
    # )

    # modality_group = defaultdict(list)

    # for series_uid, instances in meta.items():
    #     modality = instances[0]["Modality"]

    #     match modality:
    #         case "RTSTRUCT" | "RTPLAN" | "RTDOSE" | "SEG":
    #             modality_group[modality].append(instances[0])
    #         case _:
    #             modality_group[modality].extend(instances)

    # keys = list(meta.keys())

    # # Group by Modality
    # modality_group = defaultdict(list)
    # for key in keys:
    #     modality = meta[key][0]["Modality"]
    #     match modality:
    #         case "RTSTRUCT" | "RTPLAN" | "RTDOSE" | "SEG":
    #             # should only be one instance
    #             modality_group[modality].append(meta[key][0])
    #         case _:
    #             modality_group[modality].extend(meta[key])

    # # create a hashmap of
    # # sop_instance_uid -> series_instance_uid

    # sop_to_series_map = {}
    # for series_uid, items in x.items():
    #     for item in items:
    #         sop_instance_uid = item["SOPInstanceUID"]
    #         sop_to_series_map[sop_instance_uid] = series_uid

    # start = time.time()
    # for instance in tqdm(
    #     modality_group["RTPLAN"], desc="Mapping RTPLAN instances"
    # ):
    #     instance["ReferencedSeriesUID"] = sop_to_series_map[
    #         instance["ReferencedRTStructInstanceUID"]
    #     ]

    # for instance in tqdm(
    #     modality_group["RTDOSE"], desc="Mapping RTDOSE instances"
    # ):
    #     instance["ReferencedSeriesUID"] = sop_to_series_map[
    #         instance["ReferencedRTPlanInstanceUID"]
    #     ]

    # for instance in tqdm(
    #     modality_group["SEG"], desc="Mapping   SEG instances"
    # ):
    #     if "ReferencedSOPInstanceUID" in instance:
    #         if instance["ReferencedSOPInstanceUID"] in sop_to_series_map:
    #             instance["ReferencedSeriesUID"] = sop_to_series_map[
    #                 instance["ReferencedSOPInstanceUID"]
    #             ]
    #         else:
    #             errmsg = f"Could not find {instance['meta']['ReferencedSOPInstanceUID']=} in mapping"
    #             raise ValueError(errmsg)
    #     elif "ReferencedSeriesUID" in instance:
    #         assert instance["ReferencedSeriesUID"] in x
    #     else:
    #         errmsg = "Something went wrong"
    #         raise ValueError(errmsg)

    # rprint(f"Remapping instances took {time.time() - start:.2f} seconds")
    # new_series_dicts = []

    # for series_uid, instances in x.items():
    #     modality = instances[0]["Modality"]
    #     patient = instances[0]["PatientID"]
    #     study = instances[0]["StudyInstanceUID"]

    #     ref_series = instances[0].get("ReferencedSeriesUID", None)

    #     new_series_dicts.append(
    #         {
    #             "PatientID": patient,
    #             "StudyInstanceUID": study,
    #             "SeriesInstanceUID": series_uid,
    #             "Modality": modality,
    #             "ReferencedSeriesUID": ref_series,
    #         }
    #     )

    # rprint(f"Total time: {time.time() - all_start:.2f} seconds")
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
