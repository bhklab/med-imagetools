import json
import pathlib
import typing as t
from collections import defaultdict
from typing import Optional

import pandas as pd
from dpath import (
    search as dpath_search,
)
from joblib import Parallel, delayed  # type: ignore
from tqdm import tqdm

from imgtools.dicom.dicom_find import find_dicoms
from imgtools.dicom.dicom_metadata import extract_metadata
from imgtools.loggers import logger
from imgtools.utils import timed_context, timer

# __all__ export
__all__ = [
    "parse_dicom_dir",
    "SopSeriesMap",
    "SeriesMetaMap",
    "SopUID",
    "SeriesUID",
    "SubSeriesID",
]

###################################################################################################
# Helper types
###################################################################################################


SeriesUID: t.TypeAlias = str
"""Represent the `SeriesInstanceUID` of a DICOM file."""


SubSeriesID: t.TypeAlias = str
"""Represent the `AcquisitionNumber` of a DICOM file."""


SopUID: t.TypeAlias = str
"""Represent the `SOPInstanceUID` of a DICOM file."""


SeriesMetaMap: t.TypeAlias = dict[SeriesUID, dict[SubSeriesID, dict]]
"""Datatype represents: {`Series`: {`SubSeries`: `dict`}}"""

SopSeriesMap: t.TypeAlias = dict[SopUID, SeriesUID]
"""Datatype represents: {`SOPInstanceUID`: `SeriesInstanceUID`}"""


# Add this outside of any function, at the module level
def extract_metadata_wrapper(
    dicom: pathlib.Path,
) -> dict[str, object | list[object]]:
    """Wrapper for extract_metadata to avoid lambda in parallel processing."""
    return extract_metadata(dicom, None, ["SOPInstanceUID"])


@timer("Parsing all DICOMs")
def parse_all_dicoms(
    dicom_files: list[pathlib.Path],
    top: pathlib.Path,
    n_jobs: int = -1,
) -> tuple[SeriesMetaMap, SopSeriesMap]:
    """Parse a list of DICOM files in parallel and return the metadata.

    Given a list of dicom files, this function will parse the metadata of each file
    in parallel and return two dictionaries:
    1. `series_meta_raw`: A dictionary mapping `SeriesInstanceUID` to
        1 or more `SubSeriesID` and the metadata of each SubSeries.
        where `SubSeriesID` is the `AcquisitionNumber` of the DICOM file.
    2. `sop_map`: A dictionary mapping `SOPInstanceUID` to `SeriesInstanceUID`.

    ```
    {
        <SeriesInstanceUID>: {
            <SubSeriesID>: {
                'Modality': <Modality>,
                ...
                'folder': <folder>,
                'instances': {
                        <SOPInstanceUID>: <filename>,
                        ...
                    },
                }
            }
    }

    {
        <SOPInstanceUID>: <SeriesInstanceUID>,
    }
    ```
    Parameters
    ----------
    dicom_files : list[str]
        List of paths to DICOM files to process
    top : pathlib.Path
        Top directory path (used for relative path calculation)
    n_jobs : int, default=-1
        Number of parallel jobs to run
    """

    series_meta_raw: SeriesMetaMap = defaultdict(lambda: defaultdict(dict))
    sop_map: SopSeriesMap = {}
    description = f"Parsing {len(dicom_files)} DICOM files"

    for dcm, result in zip(
        dicom_files,
        Parallel(n_jobs=n_jobs, return_as="generator")(
            delayed(extract_metadata_wrapper)(dicom)
            for dicom in tqdm(
                dicom_files,
                desc=description,
                mininterval=1,
                leave=False,
                colour="green",
            )
        ),
        strict=False,
    ):
        series_uid = result["SeriesInstanceUID"]
        sop_uid = result["SOPInstanceUID"]

        # we cant let the subseries id be None or "None"
        subseries_id = SubSeriesID(result.get("AcquisitionNumber") or "1")
        if subseries_id == "None":
            subseries_id = "1"

        series_entry = series_meta_raw[series_uid][subseries_id]
        filepath: pathlib.Path = pathlib.Path(dcm).relative_to(top.parent)

        # Initialize metadata if not already set
        if "instances" not in series_entry:
            # Copy only the metadata you want to retain
            series_entry.update(
                {
                    k: v
                    for k, v in result.items()
                    if k
                    not in (
                        "SOPInstanceUID",
                    )  # exclude instance-specific keys
                }
            )
            series_entry["folder"] = str(filepath.parent.as_posix())
            series_entry["instances"] = {}

        # Append current instance info
        series_entry["instances"][sop_uid] = filepath.name  # type: ignore

        # Add the SOP UID to the sop_map dictionary
        sop_map[sop_uid] = series_uid

    return series_meta_raw, sop_map


def series2modality(
    seriesuid: SeriesUID, series_meta_raw: SeriesMetaMap
) -> str:
    """Get the modality of a series."""
    return list(series_meta_raw[seriesuid].values())[0].get("Modality", "")


def resolve_reference_series(
    meta: dict,
    sop_map: SopSeriesMap,
    series_meta_raw: SeriesMetaMap,
    frame_mapping: dict[str, set[str]],
) -> None:
    """Process reference mapping for a single metadata entry.

    The goal is to get the `ReferencedSeriesUID` for as many series as possible.
    Whereas some series directly reference the `SeriesInstanceUID` of another series,
    others reference one or more `SOPInstanceUID` of instances in another series.
    This method tries to resolve the latter case by mapping the `SOPInstanceUID` to the
    `SeriesInstanceUID` of the series it belongs to.

    Additionally, the `PT` modalities might reference a `CT`.

    Side effects:
    - as we iterate over the metadata dictionaries, we add the
        `ReferencedSeriesUID` field to the metadata dictionaries in the crawldb.

    Notes
    -----
    This mutates the metadata dictionaries in the crawldb in place.
    i.e the `ReferencedSeriesUID` field is added to metadata dicts in the crawldb.

    Parameters
    ----------
    meta : dict
        Metadata entry to process
    sop_map : dict
        Dictionary mapping SOP UIDs to Series UIDs
    series_meta_raw : dict
        Series metadata dictionary
    frame_mapping : dict
        Frame of reference mapping
    """

    if (ref := meta.get("ReferencedSeriesUID")) and ref in series_meta_raw:
        return
    else:
        meta["ReferencedSeriesUID"] = ""

    match meta["Modality"]:
        case "SEG" | "RTSTRUCT" | "RTDOSE" | "RTPLAN":
            if not (sop_refs := meta.get("ReferencedSOPUIDs", [])):
                return
            # get the unique SeriesUIDs by looking up the SOP UIDs in the sop_map
            _all_seg_refs = {
                seriesuid
                for ref in sop_refs
                if (seriesuid := sop_map.get(ref))
                and seriesuid in series_meta_raw
            }

            if not _all_seg_refs:
                # unlikely to happen...
                warnmsg = (
                    f"Referenced SOP UID {sop_refs} not found in series map"
                )
                logger.warning(
                    warnmsg,
                    modality=meta["Modality"],
                    series=meta["SeriesInstanceUID"],
                )
                return
            elif len(_all_seg_refs) > 1:
                # even more unlikely to happen...
                warnmsg = (
                    "Multiple series referenced"
                    f" ({_all_seg_refs}). Taking the first one."
                )
                logger.warning(
                    warnmsg,
                    modality=meta["Modality"],
                    series=meta["SeriesInstanceUID"],
                )
            ref_series = _all_seg_refs.pop()
            meta["ReferencedSeriesUID"] = ref_series
        case "PT":
            if (
                not (ref_frame := meta.get("FrameOfReferenceUID"))
                or not isinstance(ref_frame, str)
                or ref_frame not in frame_mapping
            ) or not (ref_series_set := frame_mapping.get(ref_frame)):
                return
            for series_uid in ref_series_set:
                if series_uid in series_meta_raw and (
                    series2modality(series_uid, series_meta_raw) == "CT"
                ):
                    meta["ReferencedSeriesUID"] = series_uid
                    break
    return


ParseDicomDirResult = t.NamedTuple(
    "ParseDicomDirResult",
    [
        ("crawl_db", list[dict[str, str]]),
        ("index", pd.DataFrame),
        ("crawl_db_raw", SeriesMetaMap),
        ("crawl_db_path", pathlib.Path),
        ("index_csv_path", pathlib.Path),
        ("crawl_cache_path", pathlib.Path),
        ("sop_map_path", pathlib.Path),
    ],
)


def parse_dicom_dir(
    dicom_dir: str | pathlib.Path,
    output_dir: str | pathlib.Path,
    dataset_name: str | None = None,
    extension: str = "dcm",
    n_jobs: int = -1,
    force: bool = True,
) -> ParseDicomDirResult:
    """Parse all DICOM files in a directory and return the metadata.

    This function searches for DICOM files within the specified directory
    (including subdirectories), extracts metadata from each file, and
    organizes the metadata into structured dictionaries.  The results,
    including a simplified crawl database, the raw series metadata,
    a SOP map, and their corresponding JSON file paths, are returned
    as a `ParseDicomDirResult` namedtuple.

    Parameters
    ----------
    dicom_dir : str | pathlib.Path
        The directory to search for DICOM files.
    output_dir : str | pathlib.Path
        The directory to save crawl outputs.
        See Notes for details.
    dataset_name : str | None, default=None
        The name of the dataset. If None, the name of the top directory
        will be used. This is used to create a subdirectory in the
        `output_dir` to store the crawl database and SOP map JSON files.
    extension : str, default="dcm"
        The file extension to look for when searching for DICOM files.
    n_jobs : int, default=-1
        The number of parallel jobs to use for parsing DICOM files.  If -1,
        all available cores will be used.
    force : bool, default=True
        If True, overwrite existing crawl database and SOP map JSON files.
        If False, load existing files if they exist.

    Returns
    -------
    ParseDicomDirResult
        A namedtuple containing the following fields:
            - crawl_db_path (pathlib.Path):
                Path to the simplified crawl database JSON file.
            - crawl_db (list[dict[str, str]]):
                A list of dictionaries containing the simplified crawl database.

    Notes
    -----
    This function will create a directory structure for the crawl database
    ```
    output_dir
        ├── <dataset_name>
        │   ├── crawl_db.json
        │   ├── crawl-cache.json
        │   ├── sop_map.json
        │   └── index.csv
        └── ...
    ```
    The `crawl_db.json` file contains the simplified crawl database, while

    """

    top = pathlib.Path(dicom_dir).absolute()
    output_dir = pathlib.Path(output_dir)
    ds_name = dataset_name or top.name

    pathlib.Path(output_dir / ds_name).mkdir(
        parents=True, exist_ok=True
    )  # create the output directory if it doesn't exist

    # determine the output directory paths
    crawl_db_path: pathlib.Path = output_dir / ds_name / "crawl_db.json"
    crawl_cache: pathlib.Path = output_dir / ds_name / "crawl-cache.json"
    sop_map_json: pathlib.Path = output_dir / ds_name / "sop_map.json"
    index_csv: pathlib.Path = output_dir / ds_name / "index.csv"

    if (crawl_cache.exists() and sop_map_json.exists()) and not force:
        logger.info(f"{crawl_cache} exists and {force=}. Loading from file.")
        with crawl_cache.open("r") as f:
            series_meta_raw = json.load(f)
        logger.info(f"{sop_map_json} exists and {force=}. Loading from file.")
        with sop_map_json.open("r") as f:
            sop_map = json.load(f)
    else:
        dicom_files = find_dicoms(top, extension=extension)
        if not dicom_files:
            msg = f"No DICOM files found in {top} with extension {extension}"
            raise FileNotFoundError(msg)

        logger.info(f"Found {len(dicom_files)} DICOM files in {dicom_dir}")

        series_meta_raw, sop_map = parse_all_dicoms(
            dicom_files, top, n_jobs=n_jobs
        )

        with crawl_cache.open("w") as f:
            json.dump(series_meta_raw, f, indent=4)
        logger.debug("Saved cache.", crawl_cache=crawl_cache)
        with sop_map_json.open("w") as f:
            json.dump(sop_map, f, indent=4)
        logger.debug("Saved SOP map.", sop_map_json=sop_map_json)

    # we have to resolve the reference series mapping
    # for the `FrameOfReferenceUID` to `SeriesInstanceUID` mapping
    # this is a bit tricky, because the `FrameOfReferenceUID` will
    # be the same for many series
    with timed_context("Mapping FrameOfReferenceUID to SeriesInstanceUID"):
        frame_mapping = defaultdict(set)
        for series_uid, subsseries_map in dpath_search(
            series_meta_raw,
            "*/**/FrameOfReferenceUID",
        ).items():
            for meta in subsseries_map.values():
                if frame := meta.get("FrameOfReferenceUID"):
                    frame_mapping[frame].add(series_uid)

    # we have to extract all the nested metadata dictionaries
    # within each subseries
    # to resolve the reference series mapping
    _meta_gen = (
        meta
        for seriesuid in series_meta_raw
        for meta in series_meta_raw[seriesuid].values()
    )

    # Using the function with the metadata generator
    for meta in tqdm(
        _meta_gen,
        desc="Solving Reference Series Mapping",
        leave=False,
    ):
        resolve_reference_series(meta, sop_map, series_meta_raw, frame_mapping)

    # add "ReferencedModality" to the metadata
    # and extract the relevant fields for barebones_dict
    slim_db = construct_barebones_dict(series_meta_raw)

    # drop duplicate entries with different subseries.
    slim_db = remove_duplicate_entries(slim_db)

    # convert slimb_db to a pandas dataframe
    index_df = pd.DataFrame.from_records(slim_db)

    index_df.to_csv(index_csv, index=False)
    logger.debug("Saved index CSV.", index_csv=index_csv)

    # save the crawl_db
    with crawl_db_path.open("w") as f:
        json.dump(series_meta_raw, f, indent=4)
    logger.debug("Saved crawl_db.", crawl_db_path=crawl_db_path)

    return ParseDicomDirResult(
        crawl_db=slim_db,
        index=index_df,
        crawl_db_raw=series_meta_raw,
        crawl_db_path=crawl_db_path,
        index_csv_path=index_csv,
        crawl_cache_path=crawl_cache,
        sop_map_path=sop_map_json,
    )


def construct_barebones_dict(
    series_meta_raw: SeriesMetaMap,
) -> list[dict[str, str]]:
    """Construct a simplified dictionary from the series metadata."""
    barebones_dict = []
    for seriesuid, subsseries_map in series_meta_raw.items():
        for subseriesid, meta in subsseries_map.items():
            match meta.get("ReferencedSeriesUID", None):
                case None | "":
                    ref_series = ""
                    meta["ReferencedModality"] = ""
                case [*multiple_refs]:  # only SR can have multiple references
                    ref_series = "|".join(multiple_refs)
                    meta["ReferencedModality"] = "|".join(
                        series2modality(ref, series_meta_raw)
                        for ref in multiple_refs
                    )
                case single_ref:
                    ref_series = single_ref
                    meta["ReferencedModality"] = series2modality(
                        ref_series, series_meta_raw
                    )

            barebones_dict.append(
                {
                    "PatientID": meta["PatientID"],
                    "StudyInstanceUID": meta["StudyInstanceUID"],
                    "SeriesInstanceUID": seriesuid,
                    "SubSeries": subseriesid or "1",
                    "Modality": meta["Modality"],
                    "ReferencedModality": meta["ReferencedModality"],
                    "ReferencedSeriesUID": meta["ReferencedSeriesUID"],
                    "instances": len(meta.get("instances", [])),
                    "folder": meta["folder"],
                }
            )

    return barebones_dict


def remove_duplicate_entries(
    slim_db: list[dict[str, str]], ignore_keys: Optional[list[str]] = None
) -> list[dict[str, str]]:
    """Removes duplicate entries from a barebones dict, ignoring the keys in `ignore_keys`.
    Parameters
    ----------

        slim_db : list[dict[str, str]]
            - The barebones dict to operate on. MUST contain the following keys:
                    "PatientID"
                    "StudyInstanceUID"
                    "SeriesInstanceUID"
                    "SubSeries"
                    "Modality"
                    "ReferencedModality"
                    "ReferencedSeriesUID"
                    "instances"
                    "folder"
        ignore_keys: Optional[list[str]], default = None
            - The list of keys to ignore when searching for duplicates.
            - If a row is exactly the same as another row, except for one of the keys listed in `ignore_keys`
              the row will still be considered a duplicate.


    Returns
    -------

        list[dict[str, str]]
            - the barebones dict with duplicates removed.

    Note: I tried to make this as efficient as possible, sorry if it slows down everything.
    """

    hash_values = set()
    # I find it more intuitive to pass in a list, rather than a set, but since sets are faster for our usecase I cast ignore_keys to a set.
    if ignore_keys is None:
        ignore_set = set(["SubSeries"])
    else:
        ignore_set = set(ignore_keys)
    output = []
    for record in slim_db:
        hash_key = [record[key] for key in record if key not in ignore_set]
        if (*hash_key,) not in hash_values:
            output.append(record)
            hash_values.add((*hash_key,))

    return output
