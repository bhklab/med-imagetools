from dataclasses import dataclass, field, fields
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
        return [field.name for field in fields(self)]

    def items(self) -> List[tuple[str, str]]:
        return [(field.name, getattr(self, field.name)) for field in fields(self)]

    def __getitem__(self, key: str) -> str:
        return getattr(self, key)

    def __rich_repr__(self) -> Iterator[tuple[str, str | Sequence[str]]]:
        # for each key-value pair, 'yield key, value'
        for attr_field in fields(self):
            if attr_field.name.endswith("ROINames"):
                if attr_field.name == "OriginalROINames":
                    continue  # skip OriginalROINames for brevity
                sorted_names = sorted(getattr(self, attr_field.name))
                yield attr_field.name, sorted_names
            else:
                yield attr_field.name, getattr(self, attr_field.name)


class ContourSlice:
    """Represents the contour points for a single slice."""

    def __init__(self, points: np.ndarray) -> None:
        assert isinstance(points, np.ndarray)
        if points.ndim != 2 or points.shape[1] != 3:
            msg = f"Contour points must be a 2D array with shape (n_points, 3), got {points.shape}"
            raise ValueError(msg)
        self.points: np.ndarray = points

    def __array__(self) -> np.ndarray:
        """Allow the object to be used as a NumPy array."""
        return self.points

    def __repr__(self) -> str:
        return f"ContourSlice<points.shape={self.points.shape}>"


@dataclass
class ROI:
    """Represents a region of interest (ROI), containing slices of contours."""

    name: str
    slices: List[ContourSlice] = field(default_factory=list)

    def add_slice(self, points: np.ndarray) -> None:
        """Add a new slice to the ROI."""
        self.slices.append(ContourSlice(points))

    def __repr__(self) -> str:
        return f"ROI<name={self.name}, num_slices={len(self.slices)}>"

    def __len__(self) -> int:
        return len(self.slices)

    def __iter__(self) -> Iterator:
        return iter(self.slices)
