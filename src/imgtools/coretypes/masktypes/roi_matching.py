from __future__ import annotations

import re
from collections import defaultdict
from enum import Enum
from functools import lru_cache
from itertools import product
from typing import Annotated, ClassVar

from pydantic import BaseModel, Field, field_validator

from imgtools.loggers import logger

__all__ = [
    "ROIMatcher",
    "ROIMatchStrategy",
    "handle_roi_matching",
    "ROIMatchFailurePolicy",
    "ROIMatchingError",
]


class ROIMatchingError(ValueError):
    """Custom exception for ROI matching failures.

    Provides detailed information about the ROIs and patterns that failed to match.
    """

    def __init__(
        self,
        message: str,
        roi_names: list[str],
        match_patterns: ROIGroupPatterns,
    ) -> None:
        """Initialize with detailed information about the matching failure.

        Parameters
        ----------
        message : str
            Base error message
        roi_names : list[str]
            ROI names that were being matched
        match_patterns : ROIGroupPatterns
            The pattern dictionary that was used for matching
        """
        self.roi_names = roi_names
        self.match_patterns = match_patterns

        # Build detailed error message
        detailed_message = f"{message}\n\n"
        detailed_message += "ROI Matching Details:\n"
        detailed_message += (
            f"- ROIs to match ({len(roi_names)}): {roi_names}\n"
        )
        detailed_message += f"- Pattern groups ({len(match_patterns)}): {{\n"

        for key, patterns in match_patterns.items():
            detailed_message += f"    '{key}': {patterns}\n"

        detailed_message += "  }\n"
        detailed_message += "\nPlease check your ROI names and match patterns."

        super().__init__(detailed_message)


# we should rename this to be intuitive
class ROIMatchStrategy(str, Enum):  # noqa: N801
    """Enum for ROI handling strategies."""

    # merge all ROIs with the same key
    MERGE = "merge"

    # for each key, keep the first ROI found based on the pattern
    KEEP_FIRST = "keep_first"

    # separate all ROIs
    SEPARATE = "separate"


class ROIMatchFailurePolicy(str, Enum):
    """Policy for how to handle total match failure (when no ROIs match any patterns)."""

    # Ignore the issue and continue silently
    IGNORE = "ignore"

    # Log a warning but continue execution
    WARN = "warn"

    # Raise an error and halt execution
    ERROR = "error"


PatternString = str
ROIGroupPatterns = dict[str, list[PatternString]]

Valid_Inputs = (
    ROIGroupPatterns
    | dict[str, PatternString]
    | list[PatternString]
    | PatternString
    | None
)
"""These are the valid inputs for the ROI matcher.
1) A dictionary with keys as strings and values as lists of regex patterns.
2) A dictionary with keys as strings and value as a single (str) regex pattern.
2) A list of regex patterns.
3) A single regex pattern as a string.
"""


def create_roi_matcher(
    nonvalidated_input: Valid_Inputs,
    handling_strategy: ROIMatchStrategy = ROIMatchStrategy.MERGE,
    ignore_case: bool = True,
    allow_multi_key_matches: bool = True,
    on_missing_regex: ROIMatchFailurePolicy = ROIMatchFailurePolicy.WARN,
) -> ROIMatcher:
    return ROIMatcher(
        match_map=ROIMatcher.validate_match_map(nonvalidated_input),
        handling_strategy=handling_strategy,
        ignore_case=ignore_case,
        allow_multi_key_matches=allow_multi_key_matches,
        on_missing_regex=on_missing_regex,
    )


class ROIMatcher(BaseModel):
    match_map: Annotated[
        ROIGroupPatterns,
        Field(description="Flexible input for ROI matcher"),
    ]
    handling_strategy: ROIMatchStrategy = ROIMatchStrategy.MERGE
    ignore_case: bool = True
    allow_multi_key_matches: bool = True
    """Whether to allow one ROI to match multiple keys in the match_map.
    
    When set to False, an ROI will only be associated with the first key 
    it matches, based on the order of keys in the match_map.
    
    Example:
        With match_map = {'gtv': 'GTV.*', 'tumor': 'GTVp.*'}
        ROI name "GTVp" would match both 'gtv' and 'tumor' patterns.
        
        If allow_multi_key_matches=True: "GTVp" appears in both key results
        If allow_multi_key_matches=False: "GTVp" only appears in 'gtv' results
    """

    on_missing_regex: ROIMatchFailurePolicy = ROIMatchFailurePolicy.WARN
    """How to handle when no ROI matches any pattern in match_map.
    
    - IGNORE: Silently continue execution
    - WARN: Log a warning but continue execution
    - ERROR: Raise an error and halt execution
    
    Note: This only applies when NO ROIs match ANY patterns. If at least one ROI
    matches at least one pattern, this policy is not activated.
    """

    default_key: ClassVar[str] = "ROI"

    @field_validator("match_map", mode="before")
    @classmethod
    def validate_match_map(cls, v: Valid_Inputs) -> ROIGroupPatterns:
        if not v:
            logger.debug(f"Empty ROI map provided {v=} . Defaulting to .*")
            return {cls.default_key: [".*"]}

        match v:
            case dict():
                cleaned = {}
                for k, val in v.items():
                    if isinstance(val, str):
                        cleaned[k] = [val]
                    elif isinstance(val, list):
                        cleaned[k] = val
                    else:  # pragma: no cover
                        msg = f"Invalid type for key '{k}': {type(val)}"
                        raise TypeError(msg)
                return cleaned
            case list():
                return {cls.default_key: v}
            case str():
                return {cls.default_key: [v]}
            case _:  # pragma: no cover
                msg = f"Unrecognized ROI matching input type: {type(v)}"
                raise TypeError(msg)

    def match_rois(self, roi_names: list[str]) -> list[tuple[str, list[str]]]:
        """
        Match ROI names against the provided patterns.

        Parameters
        ----------
        roi_names : list[str]
            List of ROI names to match.

        Returns
        -------
        list[tuple[str, list[str]]]
            List of tuples containing the key and matched ROI names.
            See `handle_roi_matching` for notes on the handling strategies.

        See Also
        --------
        handle_roi_matching : Function to handle the matching logic.
        """
        return handle_roi_matching(
            roi_names,
            self.match_map,
            self.handling_strategy,
            ignore_case=self.ignore_case,
            allow_multi_key_matches=self.allow_multi_key_matches,
        )


def handle_roi_matching(  # noqa: PLR0912
    roi_names: list[str],
    roi_matching: ROIGroupPatterns,
    strategy: ROIMatchStrategy,
    ignore_case: bool = True,
    allow_multi_key_matches: bool = True,
) -> list[tuple[str, list[str]]]:
    """
    Match ROI names against regex patterns and apply a handling strategy.

    Parameters
    ----------
    roi_names : list[str]
        List of ROI names to match.
    roi_matching : ROIGroupPatterns
        Mapping of keys to list of regex patterns.
    strategy : ROIMatchStrategy
        Strategy to use: MERGE, KEEP_FIRST, or SEPARATE.
    ignore_case : bool
        Whether to ignore case during matching.
    allow_multi_key_matches : bool
        Whether to allow an ROI to match multiple keys in the match_map.
        If False, an ROI will only be associated with the first key it matches,
        based on the order of keys in the roi_matching dictionary.
    on_missing_regex :ROIMatchFailurePolicy
        How to handle when no ROI matches any pattern in roi_matching.
        IGNORE: Silently continue execution
        WARN: Log a warning but continue execution
        ERROR: Raise an error and halt execution
        Note: This parameter is processed at the caller level, not within this function.

    Returns
    -------
    list[tuple[str, list[str]]]
        List of tuples containing the key and matched ROI names.
        See Notes for details on the handling strategies.

    Notes
    -----
    - MERGE: Merge all ROIs with the same key. Returns a single tuple for each key,
        but the value is a list of all the matched ROIs.
        i.e [('GTV', ['GTV1', 'GTV2']), ('PTV', ['PTV1', 'ptv x'])]
    - KEEP_FIRST: For each key, keep the first ROI found based on the pattern.
        Returns a single tuple for each key, but the value is a list of size ONE with
        the first matched ROI.
        i.e [('GTV', ['GTV1']), ('PTV', ['PTV1'])]
    - SEPARATE: Separate all ROIs. Returns possibly multiple tuples for each key,
        because a key may have multiple ROIs matching the pattern.
        i.e [('GTV', ['GTV1']), ('GTV', ['GTV2']), ('PTV', ['PTV1'])]

    Complex Interaction with allow_multi_key_matches:

    When allow_multi_key_matches=True:
        - One ROI can match to multiple keys
        - The strategy then only determines how ROIs are organized within
            each key group

    When allow_multi_key_matches=False:
        - Each ROI is assigned to exactly one key at most (the first matching key)
        - Strategy application happens AFTER this restriction

    Example 1:
        roi_names=['GTVp', 'GTVn', 'PTV']
        match_map={'gtv': ['GTV.*'], 'primary': ['GTVp'], 'ptv': ['PTV']}

        With allow_multi_key_matches=True:
            - MERGE: [('gtv', ['GTVp', 'GTVn']), ('primary', ['GTVp']), ('ptv', ['PTV'])]
            - KEEP_FIRST: [('gtv', ['GTVp']), ('primary', ['GTVp']), ('ptv', ['PTV'])]
            - SEPARATE: [('gtv', ['GTVp']), ('gtv', ['GTVn']), ('primary', ['GTVp']), ('ptv', ['PTV'])]

        With allow_multi_key_matches=False:
            **note that primary's GTVp got matched already in 'gtv'**
            **and thus is never added to the results**
            - MERGE: [('gtv', ['GTVp', 'GTVn']), ('ptv', ['PTV'])]
            - KEEP_FIRST: [('gtv', ['GTVp']), ('ptv', ['PTV'])]
            - SEPARATE: [('gtv', ['GTVp']), ('gtv', ['GTVn']), ('ptv', ['PTV'])]

    Example 2 (demonstrating the key issue):
        roi_names=['GTVp', 'GTVp_2']
        match_map={'primary': ['GTVp'], 'gtv': ['GTV.*']}

        With allow_multi_key_matches=True:
            - KEEP_FIRST: [('primary', ['GTVp']), ('gtv', ['GTVp'])]  # GTVp appears in both keys

        With allow_multi_key_matches=False:
            **though technically, GTVp_2 wouldve matched in 'primary', since its KEEP_FIRST,**
            **its still available for 'gtv'**
            - KEEP_FIRST: [('primary', ['GTVp']), ('gtv', ['GTVp_2'])]
    """
    flags = re.IGNORECASE if ignore_case else 0

    @lru_cache(maxsize=128)
    def _match_pattern(roi_name: str, pattern: PatternString) -> bool:
        return re.fullmatch(pattern, roi_name, flags=flags) is not None

    # First pass: collect all potential matches without considering allow_multi_key_matches
    raw_results = defaultdict(list)
    for key, patterns in roi_matching.items():
        for pattern, roi_name in product(patterns, roi_names):
            if _match_pattern(roi_name, pattern):
                raw_results[key].append(roi_name)

    # If no matches were found, return an empty list
    # The ROIMatchFailurePolicy is now handled in the caller
    if not any(raw_results.values()):
        return []

    # Apply the selected strategy to the filtered results
    # TODO:: this is a ugly mess, apologies if youre about to read this
    # TODO:: refactor!!!
    match strategy:
        case ROIMatchStrategy.MERGE:
            # Merge all ROIs with the same key
            # Returns a single tuple for each key with all matched ROIs
            filtered_results = defaultdict(list)
            assigned_rois = set()
            for key, rois in raw_results.items():
                for roi in rois:
                    if allow_multi_key_matches:
                        filtered_results[key].append(roi)
                    elif roi not in assigned_rois:
                        filtered_results[key].append(roi)
                        assigned_rois.add(roi)
            return [(key, v) for key, v in filtered_results.items() if v]
        case ROIMatchStrategy.KEEP_FIRST:
            # For each key, keep only the first ROI found
            # Returns a single tuple for each key with at most one ROI
            # more complex than it seems
            filtered_results = defaultdict(list)
            assigned_rois = set()
            for key, rois in raw_results.items():
                for roi in rois:
                    if allow_multi_key_matches:
                        # If allowing multi-key matches, keep the first match
                        filtered_results[key].append(roi)
                        break
                    elif roi not in assigned_rois:
                        filtered_results[key].append(roi)
                        assigned_rois.add(roi)
                        break  # Stop after the first match
            return [(key, v) for key, v in filtered_results.items() if v]
        case ROIMatchStrategy.SEPARATE:
            # Separate all ROIs
            # Returns one tuple per ROI
            tuples = []
            filtered_results = defaultdict(list)
            assigned_rois = set()
            for key, rois in raw_results.items():
                for roi in rois:
                    if allow_multi_key_matches:
                        filtered_results[key].append(roi)
                    elif roi not in assigned_rois:
                        filtered_results[key].append(roi)
                        assigned_rois.add(roi)
            # Flatten the results into tuples
            # This is a bit tricky because we want to keep the key
            # but separate the ROIs
            for key, v in filtered_results.items():
                for roi in v:
                    tuples.append((key, [roi]))
            return tuples
