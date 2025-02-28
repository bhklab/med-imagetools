# %% Imports

import json
import os
from pathlib import Path
from rich import print
import dpath
import pandas as pd
from imgtools.logging import logger

# %%
datadir = "testdata"

top = Path.cwd().parent.parent.parent
n_jobs = os.cpu_count()
cache_file = top / ".imgtools" / "cache" / f"{datadir}.json"
merge_series_meta_main = json.load(cache_file.open("r"))


sop_map_file = cache_file.parent / "sop_map.json"
sop_map = json.load(sop_map_file.open("r"))


# %%

all_series = list(merge_series_meta_main.values())

# %%
# filter all_series if "ReferencedSOPInstanceUID" exists

for i in all_series:
    match i["Modality"]:
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

        #     sop = dpath.get(i, "ReferencedSOPInstanceUID")
        #     print(sop)
        #     series = sop_map.get(sop)
        #     print(series)
        # print(merge_series_meta_main[series])
        # case "RTDOSE":
        #     sop = dpath.get(i, "ReferencedSOPInstanceUID")
        #     print(sop)
        #     series = sop_map.get(sop)
        #     print(series)
        # print(merge_series_meta_main[series])


# %%
