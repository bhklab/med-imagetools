import json
import os
import pathlib
import typing as t
from collections import defaultdict

from dpath import merge  # type: ignore
from joblib import Parallel, delayed  # type: ignore
from pydicom import FileDataset
from tqdm import tqdm

from imgtools.dicom import find_dicoms, load_dicom
from imgtools.dicom.input import (
    RTDOSERefPlanSOP,
    RTDOSERefSeries,
    RTDOSERefStructSOP,
    RTPLANRefStructSOP,
    RTSTRUCTRefSeries,
    RTSTRUCTRefSOP,
    RTSTRUCTRefStudy,
    SEGRefSeries,
    SEGRefSOPs,
    SR_RefSeries,
    SR_RefSOPs,
    rtdose_reference_uids,
    rtplan_reference_uids,
    rtstruct_reference_uids,
    seg_reference_uids,
    sr_reference_uids,
)
from imgtools.logging import logger, tqdm_logging_redirect
from imgtools.utils import timer

__all__ = [
    "SeriesUID",
    "SubSeriesID",
    "SopUID",
    "MetaAttrDict",
    "SeriesMetaMap",
    "SeriesMetaListMap",
    "SopSeriesMap",
    "parse_dicom_dir",
    "parse_one_dicom",
]
###################################################################################################
# Helper types
###################################################################################################


class SeriesUID(str):
    """Represent the `SeriesInstanceUID` of a DICOM file."""

    pass


class SubSeriesID(str):
    """Represent the `AcquisitionNumber` of a DICOM file."""

    pass


class SopUID(str):
    """Represent the `SOPInstanceUID` of a DICOM file."""

    pass


# A lightweight subclass of dict that allows for attribute access
class MetaAttrDict(dict):
    def __getattr__(self, key: str) -> str | list:
        return self[key]

    def __setattr__(self, key: str, value: str | list | dict) -> None:
        self[key] = value


SeriesMetaMap: t.TypeAlias = dict[SeriesUID, dict[SubSeriesID, MetaAttrDict]]
"""Datatype represents: {`Series`: {`SubSeries`: `MetaAttrDict`}}"""

SeriesMetaListMap: t.TypeAlias = dict[
    SeriesUID, dict[SubSeriesID, list[MetaAttrDict]]
]  # fmt : skip
"""Datatype represents: {`Series`: {`SubSeries`: [`MetaAttrDict`,...]}}"""

SopSeriesMap: t.TypeAlias = dict[SopUID, SeriesUID]
"""Datatype represents: {`SOPInstanceUID`: `SeriesInstanceUID`}"""

###################################################################################################
# Main functions
###################################################################################################

TAGS_OF_INTEREST = [
    "PatientID",
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "Modality",
    "FrameOfReferenceUID",
]


def update_modality_specific_references(  # noqa: PLR0912
    dcm: FileDataset, meta: MetaAttrDict
) -> None:
    """
    Update metadata with modality-specific references from the DICOM object.

    Parameters
    ----------
    dcm : pydicom.dataset.Dataset
        The DICOM object to extract references from
    meta : MetaAttrDict
        The metadata dictionary to update in-place
    """
    # Modality specific parsing. Get the references
    match meta["Modality"]:
        case "RTSTRUCT":  # simplest case
            match rtstruct_reference_uids(dcm):
                case RTSTRUCTRefSeries(rt_ref_series), RTSTRUCTRefStudy(rt_ref_study):  # fmt: skip
                    meta.ReferencedSeriesUID = rt_ref_series
                    meta.ReferencedStudyUID = rt_ref_study
                case RTSTRUCTRefSOP(rt_ref_sop):  # series reference missing
                    meta.ReferencedSOPUIDs = rt_ref_sop
        case "SEG":
            match seg_reference_uids(dcm):
                case SEGRefSeries(seg_ref_uid), SEGRefSOPs(seg_ref_sops):
                    meta.ReferencedSeriesUID = seg_ref_uid
                    meta.ReferencedSOPUIDs = seg_ref_sops
                case SEGRefSOPs(seg_ref_sops):  # no series reference
                    meta.ReferencedSOPUIDs = seg_ref_sops
        case "RTDOSE":
            match rtdose_reference_uids(dcm):
                case RTDOSERefPlanSOP(dose_ref_plan),  RTDOSERefStructSOP(dose_ref_struct), RTDOSERefSeries(dose_ref_series):  # fmt: skip
                    if (
                        dose_ref_series
                    ):  # series is often missing, but sometimes present
                        meta.ReferencedSeriesUID = dose_ref_series
                    # we prioritize the rtstruct reference
                    meta.ReferencedSOPUIDs = dose_ref_struct or dose_ref_plan
                    # sejin wants to keep 'rawdata' format as well...
                    meta.ReferencedRTPlanSOPUID = dose_ref_plan
                    meta.ReferencedRTStructSOPUID = dose_ref_struct
        case "RTPLAN":
            match rtplan_reference_uids(dcm):
                case RTPLANRefStructSOP(plan_ref_struct):
                    meta.ReferencedSOPUIDs = plan_ref_struct
                    meta.ReferencedRTStructSOPUID = plan_ref_struct  # sejin
        case "SR":
            match sr_reference_uids(dcm):
                case SR_RefSeries(sr_ref_series), SR_RefSOPs(sr_ref_sops):
                    meta.ReferencedSeriesUID = sr_ref_series
                    meta.ReferencedSOPUIDs = sr_ref_sops


def parse_one_dicom(
    dcm_path: str, top: pathlib.Path
) -> t.Tuple[SeriesMetaMap, SopSeriesMap]:
    dcm = load_dicom(
        dcm_path,
        force=True,
        stop_before_pixels=True,
    )

    # Get the main metadata
    meta = MetaAttrDict({tag: dcm.get(tag) for tag in TAGS_OF_INTEREST})

    try:
        update_modality_specific_references(dcm, meta)
    except Exception as e:
        logger.error(
            f"Error updating modality-specific references for {dcm_path}: {e}",
            modality=meta.Modality,
        )

    # Extract UID and file path
    instance_uid = SopUID(dcm.get("SOPInstanceUID"))

    subseries_uid = SubSeriesID(dcm.get("AcquisitionNumber") or "1")
    series_uid = SeriesUID(meta["SeriesInstanceUID"])

    # Make paths relative
    filepath = os.path.relpath(dcm_path, top.parent)
    meta.folder = os.path.dirname(filepath)  # noqa
    meta.instances = {instance_uid: os.path.basename(filepath)}  # noqa

    # Construct return maps in a single step
    return (
        {series_uid: {subseries_uid: meta}},  # SeriesMetaMap
        {instance_uid: series_uid},  # SopSeriesMap
    )


@timer("Parsing all DICOMs")
def parse_all_dicoms(
    dicom_files: list[str],
    top: pathlib.Path,
    n_jobs: int = -1,
) -> tuple[
    dict[SeriesUID, list[dict[SubSeriesID, MetaAttrDict]]],
    dict[SopUID, SeriesUID],
]:
    """Parse a list of DICOM files in parallel and return the metadata.

    After running parse_one_dicom on all DICOM files, the results are aggregated by
    SeriesUID and SopUID.

    i.e `series_meta_raw` is a dictionary of lists of metadata dictionaries, where the
    keys are the SeriesUIDs and the values are a list of {SubSeriesID: MetaAttrDict} dictionaries.
    and `sop_map` is just a massive hash map of SopUID to SeriesUID.
    """
    series_meta_raw: dict[SeriesUID, list[dict[SubSeriesID, MetaAttrDict]]] = defaultdict(lambda: [])  # fmt: skip
    sop_map: dict[SopUID, SeriesUID] = {}
    ############################################################
    # use parallel to run parse_dicom on every item in dcms
    with tqdm_logging_redirect():
        results = Parallel(n_jobs=n_jobs)(
            delayed(parse_one_dicom)(dcm, top)
            for dcm in tqdm(
                dicom_files,
                desc="Processing DICOM files",
                mininterval=1,
                leave=False,
            )
        )

        # Aggregate the results into a single SeriesInstanceUID Key : List[MetaAttrDict] value
        for series_dict, sop_dict in results:
            for series_uid, subseries_to_meta in series_dict.items():
                series_meta_raw[series_uid].append(subseries_to_meta)

            sop_map.update(sop_dict)

    return series_meta_raw, sop_map


@timer("Merging series meta")
def merge_series_meta_main(
    series_meta_raw_dict: dict[SeriesUID, list[dict]],
    n_jobs: int = -1,
) -> dict[SeriesUID, dict]:
    """
    Merge metadata for each DICOM series in parallel.

    This function takes raw metadata dictionaries organized by series UID and merges them
    into a single metadata dictionary per series.

    Parameters
    ----------
    series_meta_raw_dict : dict[SeriesUID, list[dict]]
        Dictionary mapping each series UID to a list of metadata attribute dictionaries.
        Each dictionary in the list typically represents metadata from one DICOM file
        in that series.

    n_jobs : int, default=-1
        Number of parallel jobs to run. If -1, uses all available CPU cores.

    Returns
    -------
    dict[SeriesUID, dict]
        Dictionary mapping each series UID to its merged metadata dictionary.
        Each series now has a single, consolidated metadata dictionary instead of
        a list of individual file metadata.
    """

    def merge_metadata_by_series(
        series_meta: tuple[SeriesUID, list[dict]],
    ) -> t.Dict[SeriesUID, dict]:
        merged: dict[SeriesUID, dict] = defaultdict(dict)
        series_uid, meta_list = series_meta
        for meta in meta_list:
            # merge using dpath.merge which is a recursive dictionary merge
            # and will handle nested dictionaries where a value could be a list
            merge(merged[series_uid], meta)
        return merged

    series_meta_merged: dict[SeriesUID, dict] = {}
    with tqdm_logging_redirect():
        series_merge_results = Parallel(n_jobs=n_jobs)(
            delayed(merge_metadata_by_series)(series_meta_item)
            for series_meta_item in tqdm(
                series_meta_raw_dict.items(),
                desc="Merging series meta",
                mininterval=1,
                leave=False,
            )
        )

        for merged in series_merge_results:
            series_meta_merged.update(merged)

    return series_meta_merged


def parse_dicom_dir(
    dicom_dir: str | pathlib.Path,
    extension: str = "dcm",
    crawl_json: pathlib.Path | None = None,
    n_jobs: int = -1,
    force: bool = True,
    imgtools_dir: str = ".imgtools",
) -> tuple[
    pathlib.Path,
    dict[SeriesUID, dict[SubSeriesID, MetaAttrDict]],
    pathlib.Path,
    dict[SopUID, SeriesUID],
]:
    """Parse all DICOM files in a directory and return the metadata.

    Returns
    -------
    tuple[pathlib.Path, dict, pathlib.Path, dict]
        A tuple containing the paths to the crawl JSON file, the series metadata,
        the SOP map JSON file, and the SOP
    """
    top = pathlib.Path(dicom_dir).absolute()
    # we consider the `dataset name` as the top directory name
    dataset_name = top.name

    if crawl_json is None:
        crawl_json = (
            top.parent / imgtools_dir / f"Dataset-{dataset_name}_crawl.json"
        )
    else:
        crawl_json = pathlib.Path(crawl_json)

    # sop_map file is the same as the crawl file, named sop_map.json
    sop_map_json = crawl_json.with_name(f"Dataset-{dataset_name}_sopmap.json")

    if (crawl_json.exists() and sop_map_json.exists()) and not force:
        logger.info(f"{crawl_json} exists and {force=}. Loading from file.")
        with crawl_json.open("r") as f:
            series_meta_merged = json.load(f)
        logger.info(f"{sop_map_json} exists and {force=}. Loading from file.")
        with sop_map_json.open("r") as f:
            sop_map = json.load(f)
        # return series_meta_merged, sop_map
        return (
            crawl_json,
            series_meta_merged,
            sop_map_json,
            sop_map,
        )

    dicom_files = find_dicoms(top, extension=extension)

    logger.info(f"Found {len(dicom_files)} DICOM files in {dicom_dir}")

    series_meta_raw, sop_map = parse_all_dicoms(
        dicom_files, top, n_jobs=n_jobs
    )

    series_meta_merged = merge_series_meta_main(series_meta_raw, n_jobs=n_jobs)

    with crawl_json.open("w") as f:
        json.dump(series_meta_merged, f, indent=4)

    with sop_map_json.open("w") as f:
        json.dump(sop_map, f, indent=4)

    # log saved paths:
    logger.info(f"Saved crawl JSON to {crawl_json}")
    logger.info(f"Saved SOP map JSON to {sop_map_json}")

    return (
        crawl_json,
        series_meta_merged,
        sop_map_json,
        sop_map,
    )
