import json

# import os
import pathlib
import typing as t
from collections import defaultdict

from dpath import (
    search as dpath_search,
)
from joblib import Parallel, delayed  # type: ignore
from tqdm import tqdm

from imgtools.dicom.dicom_find import find_dicoms
from imgtools.dicom.dicom_metadata import extract_metadata
from imgtools.loggers import logger
from imgtools.utils import timed_context, timer

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


SeriesMetaMap: t.TypeAlias = dict[SeriesUID, dict[SubSeriesID, dict]]
"""Datatype represents: {`Series`: {`SubSeries`: `dict`}}"""

SopSeriesMap: t.TypeAlias = dict[SopUID, SeriesUID]
"""Datatype represents: {`SOPInstanceUID`: `SeriesInstanceUID`}"""


@timer("Parsing all DICOMs")
def parse_all_dicoms(
    dicom_files: list[pathlib.Path],
    top: pathlib.Path,
    n_jobs: int = -1,
) -> tuple[SeriesMetaMap, SopSeriesMap]:
    """Parse a list of DICOM files in parallel and return the metadata.

    After running parse_one_dicom on all DICOM files, the results are aggregated by
    SeriesUID and SopUID.

    Parameters
    ----------
    dicom_files : list[str]
        List of paths to DICOM files to process
    top : pathlib.Path
        Top directory path (used for relative path calculation)
    n_jobs : int, default=-1
        Number of parallel jobs to run


    Returns
    -------
    tuple
        series_meta_raw: Dictionary mapping SeriesUID to lists of metadata dictionaries
        sop_map: Dictionary mapping SopUID to SeriesUID
    """

    series_meta_raw: SeriesMetaMap = defaultdict(lambda: defaultdict(dict))
    sop_map: SopSeriesMap = {}
    description = f"Parsing {len(dicom_files)} DICOM files"

    for dcm, result in zip(
        dicom_files,
        Parallel(n_jobs=n_jobs, return_as="generator")(
            delayed(extract_metadata)(dicom, None, ["SOPInstanceUID"])
            for dicom in tqdm(
                dicom_files,
                desc=description,
                mininterval=1,
                leave=False,
                colour="green",
            )
        ),
    ):
        series_uid = result["SeriesInstanceUID"]
        sop_uid = result["SOPInstanceUID"]
        subseries_id = SubSeriesID(result.get("AcquisitionNumber") or "1")

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


def resolve_reference_series(
    meta: dict,
    sop_map: SopSeriesMap,
    series_meta_raw: SeriesMetaMap,
    frame_mapping: dict[str, set[str]],
) -> None:
    """Process reference mapping for a single metadata entry.

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
            meta["ReferencedSeriesUID"] = _all_seg_refs.pop()
        case "PT":
            if not (ref_frame := meta.get("FrameOfReferenceUID")):
                return
            if ref_series := frame_mapping.get(ref_frame):
                for series_uid in ref_series:
                    if series_uid in series_meta_raw:
                        meta["ReferencedSeriesUID"] = series_uid
                        break
    return


def parse_dicom_dir(
    dicom_dir: str | pathlib.Path,
    raw_output_path: pathlib.Path,
    extension: str = "dcm",
    n_jobs: int = -1,
    force: bool = True,
) -> tuple[
    pathlib.Path,
    dict[SeriesUID, dict[SubSeriesID, dict]],
    pathlib.Path,
    dict[SopUID, SeriesUID],
]:
    """Parse all DICOM files in a directory and return the metadata.

    Returns
    -------
    tuple[pathlib.Path, dict, pathlib.Path, dict]
        A tuple containing the:
        1) paths to the crawl JSON file
        2) the series metadata dictionary
        3) the SOP map JSON file
        4) and the SOP Map dictionary.
    """
    top = pathlib.Path(dicom_dir).absolute()

    # we consider the `dataset name` as the top directory name
    crawl_json = pathlib.Path(raw_output_path)

    # sop_map file is the same as the crawl file, named sop_map.json
    sop_map_json = crawl_json.with_name(crawl_json.stem + "-sop_map.json")

    if (crawl_json.exists() and sop_map_json.exists()) and not force:
        logger.info(f"{crawl_json} exists and {force=}. Loading from file.")
        with crawl_json.open("r") as f:
            series_meta_raw = json.load(f)
        logger.info(f"{sop_map_json} exists and {force=}. Loading from file.")
        with sop_map_json.open("r") as f:
            sop_map = json.load(f)
    else:
        dicom_files = find_dicoms(top, extension=extension)

        logger.info(f"Found {len(dicom_files)} DICOM files in {dicom_dir}")

        series_meta_raw, sop_map = parse_all_dicoms(
            dicom_files, top, n_jobs=n_jobs
        )

    with timed_context("Mapping FrameOfReferenceUID to SeriesInstanceUID"):
        frame_mapping = defaultdict(set)
        for series_uid, subsseries_map in dpath_search(
            series_meta_raw,
            "*/**/FrameOfReferenceUID",
        ).items():
            for meta in subsseries_map.values():
                if frame := meta.get("FrameOfReferenceUID"):
                    frame_mapping[frame].add(series_uid)

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

    # Save the results to JSON files
    crawl_json.parent.mkdir(parents=True, exist_ok=True)
    with crawl_json.open("w") as f:
        json.dump(series_meta_raw, f, indent=4)

    with sop_map_json.open("w") as f:
        json.dump(sop_map, f, indent=4)

    # log saved paths:
    logger.info(f"Saved crawl JSON to {crawl_json}")
    logger.info(f"Saved SOP map JSON to {sop_map_json}")

    return (
        crawl_json,
        series_meta_raw,
        sop_map_json,
        sop_map,
    )


if __name__ == "__main__":
    import argparse
    import time

    # Example usage
    dicom_dir = pathlib.Path("data/Head-Neck-PET-CT")
    # dicom_dir = pathlib.Path("data")
    raw_output_path = pathlib.Path("imgtools") / "dicom" / "raw" / "crawl.json"
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Parse DICOM files in a directory"
    )
    parser.add_argument(
        "--dicom_dir",
        "-d",
        type=str,
        default=dicom_dir,
        help="Directory containing DICOM files",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=raw_output_path,
        help="Path for the output JSON file",
    )
    parser.add_argument(
        "--extension",
        "-e",
        type=str,
        default="dcm",
        help="File extension to look for (default: dcm)",
    )
    parser.add_argument(
        "--jobs",
        "-j",
        type=int,
        default=-1,
        help="Number of parallel jobs (default: -1, use all cores)",
    )
    parser.add_argument(
        "--force", "-f", action="store_true", help="Overwrite existing files"
    )

    args = parser.parse_args()

    # Convert string paths to pathlib.Path objects
    dicom_dir = pathlib.Path(args.dicom_dir)
    raw_output_path = pathlib.Path(args.output)
    # Benchmark parse_dicom_dir 10 times

    times = []

    start_time = time.perf_counter()
    parse_dicom_dir(
        dicom_dir,
        raw_output_path,
        extension=args.extension,
        n_jobs=args.jobs,
        force=args.force,
    )
    end_time = time.perf_counter()
    elapsed = end_time - start_time
    times.append(elapsed)
    # print(f"Run {i + 1}: {elapsed:.4f} seconds")

    # # Print statistics
    # print("\nBenchmark results:")
    # print(f"First run time(warm-up): {times[0]:.4f} seconds")
    # times = times[1:]  # Ignore the first run for warm-up
    # avg_time = sum(times) / len(times)
    # print(f"Average time: {avg_time:.4f} seconds")
    # print(f"Min time: {min(times):.4f} seconds")
    # print(f"Max time: {max(times):.4f} seconds")

# names_generator = itk.GDCMSeriesFileNames.New(); names_generator.SetUseSeriesDetails(True); names_generator.AddSeriesRestriction('0008|0032'); names_generator.SetDirectory("data/QIN-HEADNECK/QIN-HEADNECK-01-0003/PT_Series24225617"); names_generator.GetSeriesUIDs()
