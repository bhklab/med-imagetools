from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Iterator, List, Sequence

import numpy as np


@dataclass
class RTSTRUCTMetadata:
    """Dataclass for RTSTRUCT metadata.

    New keys can be added as needed.
    """

    PatientID: str
    StudyInstanceUID: str
    SeriesInstanceUID: str
    Modality: str
    ReferencedSeriesInstanceUID: str
    OriginalROINames: Sequence[str]
    OriginalNumberOfROIs: int
    ExtractedROINames: Sequence[str] = ()
    ExtractedNumberOfROIs: int = 0

    # or 'key in RTSTRUCTMetadata' to check if a key exists
    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    def keys(self) -> List[str]:
        return [attr_field.name for attr_field in fields(self)]

    def items(self) -> List[tuple[str, str]]:
        return [(attr_field.name, getattr(self, attr_field.name)) for attr_field in fields(self)]

    def __getitem__(self, key: str) -> str:
        return getattr(self, key)

    def __rich_repr__(self) -> Iterator[tuple[str, str | Sequence[str]]]:
        # for each key-value pair, 'yield key, value'
        for attr_field in fields(self):
            if attr_field.name.endswith("ROINames"):
                if attr_field.name == "OriginalROINames":
                    continue  # skip OriginalROINames for brevity
                sorted_names = sorted(getattr(self, attr_field.name))
                yield attr_field.name, ", ".join(sorted_names)
            else:
                yield attr_field.name, getattr(self, attr_field.name)


class ContourSlice(np.ndarray):
    """Represents the contour points for a single slice.
    Simply a NumPy array with shape (n_points, 3) where the last dimension
    represents the x, y, and z coordinates of each point.
    """

    def __new__(cls, input_array: np.ndarray) -> ContourSlice:
        obj = np.asarray(input_array).view(cls)
        return obj

    def __array_finalize__(self, obj: np.ndarray | None) -> None:
        if obj is None:
            return
        assert self.ndim == 2
        assert self.shape[1] == 3

    def __repr__(self) -> str:
        return f"ContourSlice<points.shape={self.shape}>"


@dataclass
class ROI:
    """Represents a region of interest (ROI), containing slices of contours."""

    name: str
    referenced_roi_number: int
    slices: List[ContourSlice]

    def __repr__(self) -> str:
        return f"ROI<name={self.name}, roi_num={self.referenced_roi_number}, num_slices={len(self.slices)}>"

    def __len__(self) -> int:
        return len(self.slices)

    def __iter__(self) -> Iterator:
        return iter(self.slices)
