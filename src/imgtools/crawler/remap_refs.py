# %% Imports

import json
import os
from pathlib import Path

import dpath
import pandas as pd
from rich import print

from imgtools.logging import logger

# %%
datadir = "SARC021"

top = Path.cwd().parent.parent.parent / "privatedata"
n_jobs = os.cpu_count()
cache_file = top / ".imgtools" / "cache" / f"{datadir}.json"
merge_series_meta_main = json.load(cache_file.open("r"))


sop_map_file = cache_file.parent / "sop_map.json"
sop_map = json.load(sop_map_file.open("r"))


# %%

all_series = list(merge_series_meta_main.values())

# columns for df
columns = [
    "PatientID",
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "Modality",
    "FrameOfReferenceUID",
    "SubSeriesID",
    "ReferencedSeriesUID",
]


# %%
# filter all_series if "ReferencedSOPInstanceUID" exists
all_remapped_series = []
all_refd_series = []
aggregated_series = []
for metadata in all_series:
    for subseries, i in metadata.items():
        match i["Modality"]:
            case "RTSTRUCT":
                if i.get("ReferencedSeriesUID") in merge_series_meta_main:
                    pass
                elif i.get("RTSTRUCTRefSOP") in sop_map:
                    i["ReferencedSeriesUID"] = sop_map[i["RTSTRUCTRefSOP"]]  # fmt: off
                else:
                    warnmsg = (
                        f"RTSTRUCT SeriesInstanceUID={i['SeriesInstanceUID']}"
                        " has no reference"
                    )
                    logger.warning(warnmsg)

            case "SEG":
                # we want to iterate over all the referenced SOPInstanceUIDs
                # and find the corresponding SeriesInstanceUID
                # and hope that its a set of 1 element

                series_uids = set()

                for sop in i.get("ReferencedSOPInstanceUID"):
                    if sop in sop_map:
                        series_uids.add(sop_map[sop])
                    else:
                        warnmsg = (
                            f"SEG SeriesInstanceUID={i['SeriesInstanceUID']}"
                            f"references an unknown SOPInstanceUID: {sop}"
                        )
                        logger.warning(warnmsg)

                if not series_uids:
                    warnmsg = (
                        f"SEG SeriesInstanceUID={i['SeriesInstanceUID']}"
                        "has no references"
                    )
                    logger.warning(warnmsg)
                elif len(series_uids) > 1:
                    warnmsg = (
                        f"SEG SeriesInstanceUID={i['SeriesInstanceUID']}"
                        " has multiple references"
                    )
                    logger.warning(warnmsg)
                else:
                    # check if the single series UID is in the main dict
                    series_uid = series_uids.pop()
                    if series_uid in merge_series_meta_main:
                        if (
                            i.get("ReferencedSeriesInstanceUID")
                            and i["SeriesInstanceUID"] != series_uid
                        ):
                            warnmsg = (
                                f"SEG SeriesInstanceUID={i['SeriesInstanceUID']}"
                                f"references a different SeriesInstanceUID: {series_uid}"
                            )
                            logger.warning(warnmsg)
                            raise ValueError(warnmsg)

                        i["SeriesInstanceUID"] = series_uid
                    else:
                        warnmsg = (
                            f"SEG SeriesInstanceUID={i['SeriesInstanceUID']}"
                            "references an unknown SeriesInstanceUID: {series_uid}"
                        )
                        logger.warning(warnmsg)
                    all_refd_series.append(series_uid)
                all_remapped_series.append(i)
            case "RTDOSE":
                if i.get("ReferencedSeriesUID") in merge_series_meta_main:
                    continue
                if i.get("RTDOSERefStructSOP") in sop_map:
                    i["ReferencedSeriesUID"] = sop_map[i["RTDOSERefStructSOP"]]
                elif i.get("RTDOSERefPlanSOP") in sop_map:
                    i["ReferencedSeriesUID"] = sop_map[i["RTDOSERefPlanSOP"]]
                else:
                    warnmsg = (
                        f"RTDOSE SeriesInstanceUID={i['SeriesInstanceUID']}"
                        "has no reference"
                    )
                    logger.warning(warnmsg)
            case "RTPLAN":
                if i.get("RTPLANRefStructSOP") in sop_map:
                    i["ReferencedSeriesUID"] = sop_map[i["RTPLANRefStructSOP"]]
                else:
                    warnmsg = (
                        f"RTPLAN SeriesInstanceUID={i['SeriesInstanceUID']}"
                        "has no reference"
                    )
                    logger.warning(warnmsg)

                refd_sops = i.get("ReferencedSOPInstanceUID")

                if i.get("ReferencedSeriesUID") in merge_series_meta_main:
                    sop = dpath.get(i, "ReferencedSOPInstanceUID")

        aggregated_series.append([i.get(col, None) for col in columns])


# %%
# create pandas df with empty columns
aggregate_df = pd.DataFrame(aggregated_series, columns=columns)
# aggregate_df.set_index("SeriesInstanceUID", inplace=True)
aggregate_df.to_csv("SARC021.csv", index = False)

# %%
# now
