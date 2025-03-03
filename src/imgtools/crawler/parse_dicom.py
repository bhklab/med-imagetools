import json
import os
import pathlib
import time
import typing as t
from collections import defaultdict

from dpath import merge # type: ignore
from joblib import Parallel, delayed  # type: ignore
from pydicom import dcmread
from tqdm import tqdm

from imgtools.dicom import find_dicoms
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

TAGS_OF_INTEREST = [
    "PatientID",
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "Modality",
    "FrameOfReferenceUID",
]


class SeriesUID(str):
    pass


class SubSeriesID(str):
    pass


class SopUID(str):
    pass


# A lightweight subclass of dict that allows for attribute access
class MetaAttrDict(dict):
    def __getattr__(self, key: str) -> str | list:
        return self[key]

    def __setattr__(self, key: str, value: str | list | dict) -> None:
        self[key] = value


def parse_dicom(
    dcm_path: str, top: pathlib.Path
) -> t.Tuple[
    t.Dict[SeriesUID, t.Dict[SubSeriesID, MetaAttrDict]],
    t.Dict[SopUID, SeriesUID],
]:
    dcm = dcmread(
        dcm_path,
        force=True,
        stop_before_pixels=True,
    )

    meta = MetaAttrDict({tag: str(dcm.get(tag)) for tag in TAGS_OF_INTEREST})
    # TODO:: standardize the naming of the attributes we set here
    # i.e RTDOSERefPlanSOP but we use just ReferencedSOPInstanceUID
    match meta["Modality"]:
        case "RTSTRUCT":  # simplest case
            match rtstruct_reference_uids(dcm):
                case RTSTRUCTRefSeries(rt_ref_series), RTSTRUCTRefStudy(rt_ref_study):  # fmt: skip
                    meta.ReferencedSeriesUID = rt_ref_series
                    meta.ReferencedStudyUID = rt_ref_study
                case RTSTRUCTRefSOP(rt_ref_sop): # single SOP reference at the moment
                    meta.ReferencedSOPUIDs = rt_ref_sop
        case "SEG":
            match seg_reference_uids(dcm):
                case SEGRefSeries(seg_ref_uid), SEGRefSOPs(seg_ref_sops):
                    meta.ReferencedSeriesUID = seg_ref_uid
                    meta.ReferencedSOPUIDs = seg_ref_sops
                case SEGRefSOPs(seg_ref_sops):  # no series reference
                    meta.ReferencedSOPUIDs = seg_ref_sops
        case "RTDOSE":
            # this ones too complicated lol
            match rtdose_reference_uids(dcm):
                case RTDOSERefPlanSOP(dose_ref_plan),  RTDOSERefStructSOP(dose_ref_struct), RTDOSERefSeries(dose_ref_series):  # fmt: skip
                    meta.ReferencedSeriesUID = dose_ref_series
                    # we prioritize the rtstruct reference
                    meta.ReferencedSOPUIDs = dose_ref_struct or dose_ref_plan
                    # sejin wants to keep 'rawdata' format as well...
                    meta.ReferencedRTPlanSOPUID = dose_ref_plan
                    meta.ReferencedRTStructSOPUID = dose_ref_struct
        case "RTPLAN":
            match rtplan_reference_uids(dcm):
                case RTPLANRefStructSOP(plan_ref_struct):
                    meta.ReferencedSOPUIDs =plan_ref_struct 
                    meta.ReferencedRTStructSOPUID = plan_ref_struct  # sejin
        case "SR":
            match sr_reference_uids(dcm):
                case SR_RefSeries(sr_ref_series), SR_RefSOPs(sr_ref_sops):
                    meta.ReferencedSeriesUID = sr_ref_series
                    meta.ReferencedSOPUIDs = sr_ref_sops
        case _:
            pass

    # We do this separately to also build the SOPHashMap
    instance_uid = SopUID(object=dcm.get("SOPInstanceUID"))

    # We make this a dictionary so merges are straightforward
    filepath = os.path.relpath(dcm_path, top)
    meta.folder = os.path.dirname(filepath)  # noqa
    # we are going to assume that all instances for a series::acquisition are in the same folder
    meta.instances = {instance_uid: os.path.basename(filepath)}  # noqa

    raw_acq = dcm.get("AcquisitionNumber", "None")
    meta["SubSeriesID"] = str(raw_acq) if raw_acq != "None" else "default"

    # We need to keep track of the mapping between SOPInstanceUID and SeriesInstanceUID
    sop_series_map: dict[SopUID, SeriesUID] = {}
    sop_series_map[instance_uid] = SeriesUID(meta["SeriesInstanceUID"])

    series_meta_map: dict[SeriesUID, dict[SubSeriesID, MetaAttrDict]] = {}
    series_meta_map[SeriesUID(meta["SeriesInstanceUID"])] = {
        SubSeriesID(meta["SubSeriesID"]): meta
    }

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


@timer("Parsing all DICOMs")
def parse_all_dicoms(
    dicom_files: t.List[str], top: pathlib.Path
) -> t.Tuple[
    t.Dict[SeriesUID, list[MetaAttrDict]],
    t.Dict[SopUID, SeriesUID],
]:
    series_meta_raw: t.Dict[SeriesUID, list[MetaAttrDict]] = defaultdict(
        list[MetaAttrDict]
    )
    sop_map: t.Dict[SopUID, SeriesUID] = defaultdict(SeriesUID)
    ############################################################
    # use parallel to run parse_dicom on every item in dcms
    with tqdm_logging_redirect():
        results = Parallel(n_jobs=n_jobs)(
            delayed(parse_dicom)(dcm, top)
            for dcm in tqdm(
                dicom_files,
                desc="Processing DICOM files",
                mininterval=1,
                leave=False,
            )
        )

        for series_dict, sop_dict in results:
            for series_uid, meta in series_dict.items():
                series_meta_raw[series_uid].append(meta)

            sop_map.update(sop_dict)

    return series_meta_raw, sop_map


if __name__ == "__main__":
    force = True
    top = pathlib.Path("testdata").absolute()
    n_jobs = os.cpu_count()

    cache_file = top.parent / ".imgtools" / "cache" / f"{top.name}_crawl.json"
    sopmap_cache = cache_file.with_name(f"{top.name}_sop-map.json")
    
    all_start = time.time()
    if (
        cache_file.exists() and sopmap_cache.exists()
    ) and not force:
        logger.info(f"Using cache file {cache_file}")
        with cache_file.open("r") as f:
            series_meta_merged = json.load(f)
        logger.info(f'Using cache file {sopmap_cache}')
        with sopmap_cache.open("r") as f:
            sop_map = json.load(f)
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

        # setup data structures
        # series_meta_raw: t.Dict[SeriesUID, list[MetaAttrDict]] = defaultdict(
        #     list[MetaAttrDict]
        # )
        # sop_map: t.Dict[SopUID, SeriesUID] = defaultdict(SeriesUID)
        ############################################################
        # use parallel to run parse_dicom on every item in dcms

        series_meta_raw, sop_map = parse_all_dicoms(dcms, top)

        ############################################################
        # use parallel to run merge_series_meta on every item in series_meta_raw
        series_meta_merged = merge_series_meta_main(
            series_meta_raw, n_jobs=n_jobs
        )

        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with cache_file.open("w") as f:
            json.dump(
                # {"series_meta": series_meta_merged, "sop_map": sop_map}, f, indent=4
                series_meta_merged,
                f,
                indent=4,
            )

        with sopmap_cache.open("w") as f:
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
