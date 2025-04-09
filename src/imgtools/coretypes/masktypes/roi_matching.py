"""
ROIMatcher
----------
users MUST define a dictionary mapping a key (general roi identifier i.e GTV)
to a list of [exact names OR regex patterns] 
if they ONLY provide a list WITHOUT a key, the default key is "ROI" (or whatever is passed)

Valid examples:
```
roi_matcher = "GTV.*"
roi_matcher = ["GTVp", "CTV.*"]
roi_matcher = {"GTV": ["GTVp", "CTV.*"]}
roi_matcher = {"GTV": ["GTV.*"], "CTV": ["CTV.*"]}
```

Invalid examples:
```
roi_matcher = 123 # invalid because it's an int
roi_matcher = [['GTV.*', "CTV.*"]] # invalid because it's a list of lists
roi_matcher = {'GTV':{'GTVp': "GTVp.*"}, 'CTV': "CTV.*"} # invalid because it's a dict of dicts}
```

Handling
--------

Given a valid ROI_Matching input, combined with a ROI_HANDLING strategy,
we choose to build a roi_map using our roi names from the RTSTRUCT or SEG.

The roi_map is a dictionary where the keys are the names of the ROIs
and the values are lists of the names of the ROIs that match the patterns
in the ROI_Matching input.

So given
these rois (extracted names will be sorted alphabetically like this too)):
```
[
    'CTV_0',
    'CTV_1',
    'CTV_2',
    'ExtraROI',
    'ExtraROI2',
    'GTV 0',
    'GTVp',
    'PTV',
    'ptv x'
]
```

and this roi_matching input:
```
{
    "GTV": ["GTV*"],
    "PTV": ["PTV.*"],
    "TV": ["GTV.*", "PTV.*", "CTV.*"],
    "extra": ["ExtraROI", "ExtraROI2"] # can use regex or exact names
}
```

Here are the resulting extractions based on the handling strategy:
NOTE: regardless of handling strategy, the matches will be stored in some
metadata, so the user knows what was matched

`ROI_HANDLING.SEPARATE`
```
[
    "[GTV]__GTVp",
    "[GTV]__GTV_0",
    "[PTV]__PTV",
    "[PTV]__ptv_x",
    "[TV]__GTVp",
    "[TV]__GTV_0",
    "[TV]__PTV",
    "[TV]__ptv_x",
    "[TV]__CTV_0",
    "[TV]__CTV_1",
    "[TV]__CTV_2",
    "[extra]__ExtraROI",
    "[extra]__ExtraROI2",
]
```

`ROI_HANDLING.MERGE`
```
[
    "GTV",  # ["GTVp", "GTV 0"] are merged
    "PTV",  # ["PTV", "ptv x"] are merged
    "TV",   # ["GTV", "GTV 0", "PTV", "ptv x", "CTV_0", "CTV_1", "CTV_2"] are merged
    "extra" # ["ExtraROI", "ExtraROI2"] are merged
]

NOTE: `ROI_HANDLING.KEEP_FIRST` is strongly discouraged, as the first roi found is never
guaranteed to be the most relevant one.
Nonetheless, exact ROI pattern names are preferred to generalized regex matching
i.e ("CTV_0" is preferred to "CTV.*") to ensure some level of
confidence in the matching.
`ROI_HANDLING.KEEP_FIRST`
```
[
    "[GTV]__GTV_0",  # `GTV 0` comes first before `GTVp`
    "[PTV]__PTV",   # `PTV` comes first before `ptv x`

    # `CTV_0` comes first before all other matches in the sorted list 
    # BUT we specifically had 'GTV.*' first in the list
    "[TV]__GTV_0",  

    # `ExtraROI` got matched because it was an exact pattern
    "[extra]__ExtraROI",
]
```
""" 

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum, auto
from itertools import product

from pydantic import BaseModel, field_validator


# we should rename this to be intuitive
class ROI_HANDLING(Enum):  # noqa: N801
    """Enum for ROI handling strategies."""

    # merge all ROIs with the same key
    MERGE = auto()

    # for each key, keep the first ROI found based on the pattern
    KEEP_FIRST = auto()

    # separate all ROIs
    SEPARATE = auto()


PatternString = str
ROI_MatchingType = dict[str, list[PatternString]]


class ROIMatcher(BaseModel):
    roi_map: ROI_MatchingType

    @classmethod
    def from_raw(
        cls,
        raw: ROI_MatchingType | list[PatternString] | PatternString | None,
        default_key: str = "ROI",
    ) -> ROIMatcher:
        match raw:
            case dict():
                if not raw:
                    return cls(roi_map={default_key: [".*"]})
                cleaned = {}
                for k, v in raw.items():
                    if isinstance(v, str):
                        cleaned[k] = [v]
                    elif isinstance(v, list):
                        cleaned[k] = v
                    else:
                        msg = f"Invalid type for key '{k}': {type(v)}"
                        raise TypeError(msg)
                return cls(roi_map=cleaned)
            case list():
                return cls(roi_map={default_key: raw})
            case str():
                return cls(roi_map={default_key: [raw]})
            case None:
                return cls(roi_map={default_key: [".*"]})
            case _: # pragma: no cover
                msg = f"Unrecognized ROI matching input type: {type(raw)}"
                raise TypeError(msg)

    @field_validator("roi_map", mode="before")
    @classmethod
    def validate_roi_map(cls, v: ROI_MatchingType) -> ROI_MatchingType:
        assert isinstance(v, dict), "ROI map must be a dictionary."
        if not v:
            errmsg = "ROI map cannot be empty."
            raise ValueError(errmsg)
        for key, patterns in v.items():
            if not isinstance(patterns, list):
                errmsg = f"Value for key '{key}' must be a list of strings."
                raise TypeError(errmsg)
            if not all(isinstance(p, str) for p in patterns):
                errmsg = f"All patterns for key '{key}' must be strings."
                raise ValueError(errmsg)
        return v


@dataclass
class ROIMatchResult:
    key: str
    matches: list[str]  # can be many if MERGE
    strategy: ROI_HANDLING


def match_roi(
    roi_names: list[str],  # assumes already sorted
    roi_matching: ROI_MatchingType,
    ignore_case: bool,
) -> dict[str, list[str]]:
    results = defaultdict(list)
    key: str
    patterns: list[PatternString]
    flags = re.IGNORECASE if ignore_case else 0

    def _match_pattern(roi_name: str, pattern: PatternString) -> bool:
        return re.fullmatch(pattern, roi_name, flags=flags) is not None

    # this unfortunately not really efficient, can use lru_cache
    # but we don't need to optimize this for now
    for key, patterns in roi_matching.items():
        for pattern, roi_name in product(patterns, roi_names):
            if _match_pattern(roi_name, pattern):
                results[key].append(roi_name)

    # filter out any potential empty lists
    return {k: v for k, v in results.items() if v}


def handle_roi_matching(
    roi_names: list[str],
    roi_matching: ROI_MatchingType,
    strategy: ROI_HANDLING,
    ignore_case: bool = True,
) -> list[ROIMatchResult]:
    """
    Apply a matching strategy to ROI names using regex-based matching rules.

    Parameters
    ----------
    roi_names : list[str]
        List of ROI names to match.
    roi_matching : dict[str, list[str]]
        Mapping of label key to regex patterns or exact names.
    strategy : ROI_HANDLING
        Strategy for combining matches (MERGE, KEEP_FIRST, SEPARATE).
    ignore_case : bool
        Whether to ignore case when matching (default: True)

    """
    matched = match_roi(roi_names, roi_matching, ignore_case=ignore_case)
    output: list[ROIMatchResult] = []

    for key, matches in matched.items():
        if strategy == ROI_HANDLING.SEPARATE:
            for match in matches:
                output.append(
                    ROIMatchResult(key=key, matches=[match], strategy=strategy)
                )

        elif strategy == ROI_HANDLING.MERGE:
            output.append(
                ROIMatchResult(key=key, matches=matches, strategy=strategy)
            )

        elif strategy == ROI_HANDLING.KEEP_FIRST:
            # find the first match for each key
            first_match = matches[0]
            output.append(
                ROIMatchResult(
                    key=key, matches=[first_match], strategy=strategy
                )
            )
        else: # pragma: no cover
            errmsg = (
                f"Unrecognized strategy: {strategy}. Something went wrong."
            )
            raise ValueError(errmsg)

    return output
