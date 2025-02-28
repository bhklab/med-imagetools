import json
import os
import pathlib
import time
import typing as t
from collections import defaultdict

from dpath import merge
from joblib import Parallel, delayed  # type: ignore
from pydicom import dcmread
from tqdm import tqdm

from imgtools.dicom.input import (
    RTDOSERefPlanSOP,
    RTDOSERefStructSOP,
    RTDOSERefSeries,
    RTPLANRefStructSOP,
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

TAGS_OF_INTEREST = [
    "PatientID",
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "Modality",
    "FrameOfReferenceUID",
]
from imgtools.dicom import find_dicoms


class SeriesUID(str):
    pass


class SopUID(str):
    pass


# A lightweight subclass of dict that allows for attribute access
class MetaAttrDict(dict):
    def __getattr__(self, key: str) -> str | list:
        return self[key]

    def __setattr__(self, key: str, value: str | list | dict) -> None:
        self[key] = value


def parse_dicom(  # noqa: PLR0912
    dcm_path: str, top: pathlib.Path
) -> t.Tuple[t.Dict[SeriesUID, MetaAttrDict], t.Dict[SopUID, SeriesUID]]:
    dcm = dcmread(
        dcm_path,
        force=True,
        stop_before_pixels=True,
    )

    meta = MetaAttrDict({tag: str(dcm.get(tag)) for tag in TAGS_OF_INTEREST})

    # Types are inferred from the assignments in the match statement below
    match meta["Modality"]:
        case "RTSTRUCT":  # simplest case
            match rtstruct_reference_uids(dcm):
                case [rt_ref_series, _]:  # we dont care about ref study
                    meta.ReferencedSeriesUID = rt_ref_series
        case "SEG":
            match seg_reference_uids(dcm):
                case SEGRefSeries(seg_ref_uid), SEGRefSOPs(seg_ref_sops):
                    meta.ReferencedSeriesUID = seg_ref_uid
                    meta.ReferencedSOPInstanceUID = seg_ref_sops
                case SEGRefSOPs(seg_ref_sops):  # no series reference
                    meta.ReferencedSOPInstanceUID = seg_ref_sops
        case "RTDOSE":
            # this ones too complicated lol
            refd_plan, refd_struct, refd_series = rtdose_reference_uids(dcm)
            meta.ReferencedSeriesUID = str(refd_series or "")
            meta.RTDOSERefPlanSOP = str(refd_plan or "")
            meta.RTDOSERefStructSOP = str(refd_struct or "")

        case "RTPLAN":
            match rtplan_reference_uids(dcm):
                case RTPLANRefStructSOP(referenced_rtstruct_uid):
                    meta.ReferencedSOPInstanceUID = referenced_rtstruct_uid
                    meta.RTPLANRefStructSOP = referenced_rtstruct_uid  # sejin
        case "SR":
            match sr_reference_uids(dcm):
                case SR_RefSeries(sr_ref_series), SR_RefSOPs(sr_ref_sops):
                    meta.ReferencedSeriesUID = sr_ref_series
                    meta.ReferencedSOPInstanceUID = sr_ref_sops
        case _:
            pass

    # We do this separately to also build the SOPHashMap
    instance_uid = SopUID(object=dcm.get("SOPInstanceUID"))

    # We make this a dictionary so merges are straightforward
    meta.intances = {instance_uid: os.path.relpath(dcm_path, top)}

    # We need to keep track of the mapping between SOPInstanceUID and SeriesInstanceUID
    sop_series_map: dict[SopUID, SeriesUID] = {}
    sop_series_map[instance_uid] = SeriesUID(meta["SeriesInstanceUID"])

    series_meta_map: dict[SeriesUID, MetaAttrDict] = {}
    series_meta_map[SeriesUID(meta["SeriesInstanceUID"])] = meta

    return series_meta_map, sop_series_map


@timer("Merging series meta")
def merge_series_meta_main(
    series_meta_raw_dict: dict[SeriesUID, list[MetaAttrDict]],
    n_jobs: int = 1,
) -> dict[SeriesUID, MetaAttrDict]:
    """"""

    def merge_metadata_by_series(
        series_meta: tuple[SeriesUID, list[MetaAttrDict]],
    ) -> t.Dict[SeriesUID, MetaAttrDict]:
        merged: dict[SeriesUID, MetaAttrDict] = defaultdict(MetaAttrDict)
        series_uid, meta_list = series_meta
        for meta in meta_list:
            merge(merged[series_uid], meta)
        return merged

    series_meta_merged: dict[SeriesUID, MetaAttrDict] = {}
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


if __name__ == "__main__":
    force = True
    top = pathlib.Path("testdata").absolute()
    n_jobs = os.cpu_count()
    cache_file = top.parent / ".imgtools" / "cache" / f"{top.name}.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    all_start = time.time()
    if cache_file.exists() and not force:
        logger.info(f"Using cache file {cache_file}")
        with cache_file.open("r") as f:
            series_meta_merged = json.load(f)
        logger.info(
            f"Loaded {len(series_meta_merged)} series from"
            " cache in {time.time() - all_start:.2f} seconds"
        )
    else:
        # find all dicom files
        dcms: t.List[str] = [
            str(path)
            for path in find_dicoms(
                directory=top,
                recursive=True,
                check_header=False,
                extension="dcm",
            )
        ]
        logger.info(
            f"Found {len(dcms)} DICOM files in {time.time() - all_start:.2f} seconds"
        )

        logger.info(
            f"Using {n_jobs} workers for parallel processing with",
            param_n_jobs=n_jobs,
        )

        # setup data structures
        series_meta_raw: t.Dict[SeriesUID, list[MetaAttrDict]] = defaultdict(
            list[MetaAttrDict]
        )
        sop_map: t.Dict[SopUID, SeriesUID] = defaultdict(SeriesUID)
        ############################################################
        # use parallel to run parse_dicom on every item in dcms

        parse_start = time.time()
        with tqdm_logging_redirect():
            results = Parallel(n_jobs=n_jobs)(
                delayed(parse_dicom)(dcm, top)
                for dcm in tqdm(
                    dcms,
                    desc="Processing DICOM files",
                    mininterval=1,
                    leave=False,
                )
            )

            for series_dict, sop_dict in results:
                for series_uid, meta in series_dict.items():
                    series_meta_raw[series_uid].append(meta)

                sop_map.update(sop_dict)
            logger.info(
                f"Total parsing time: {time.time() - parse_start:.2f} seconds"
            )

        ############################################################
        # use parallel to run merge_series_meta on every item in series_meta_raw

        series_meta_merged = merge_series_meta_main(
            series_meta_raw, n_jobs=n_jobs
        )

        with cache_file.open("w") as f:
            json.dump(
                # {"series_meta": series_meta_merged, "sop_map": sop_map}, f, indent=4
                series_meta_merged,
                f,
                indent=4,
            )

        with (cache_file.parent / "sop_map.json").open("w") as f:
            json.dump(sop_map, f, indent=4)

    logger.info(f"Total time: {time.time() - all_start:.2f} seconds")


# ###
# s_meta: t.Dict[SeriesInstanceUID, list[MetaAttrDict]] = defaultdict(
#         list[MetaAttrDict]
#     )
# start = time.time()
# for sd, sopd in results[:500]:
#     dpath.merge(s_meta, sd);
# end = time.time()
