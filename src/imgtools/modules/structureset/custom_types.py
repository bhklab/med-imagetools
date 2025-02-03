from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Iterator, List, Sequence

import numpy as np


@dataclass
class ROIMetadata:
    """Dataclass for ROI metadata.

    New keys can be added as needed.
    """

    ROIName: str
    ROINumber: str
    ROIGenerationAlgorithm: str

    def keys(self) -> List[str]:
        return [attr_field.name for attr_field in fields(self)]

    def items(self) -> List[tuple[str, str | Sequence[str]]]:
        return [
            (attr_field.name, getattr(self, attr_field.name))
            for attr_field in fields(self)
        ]

    def to_dict(self) -> dict:
        return asdict(self)

    def __getitem__(self, key: str) -> str:
        return getattr(self, key)

    def __rich_repr__(self) -> Iterator[tuple[str, str]]:
        for attr_field in fields(self):
            yield attr_field.name, getattr(self, attr_field.name)


@dataclass
class RTSTRUCTMetadata:
    """Dataclass for RTSTRUCT metadata.

    New keys can be added as needed.
    """

    PatientID: str
    Modality: str
    StudyInstanceUID: str
    SeriesInstanceUID: str
    ReferencedStudyInstanceUID: str
    ReferencedSeriesInstanceUID: str
    OriginalROIMeta: List[ROIMetadata]
    OriginalNumberOfROIs: int

    def keys(self) -> List[str]:
        return [attr_field.name for attr_field in fields(self)]

    def items(self) -> List[tuple[str, str]]:
        return [
            (attr_field.name, getattr(self, attr_field.name))
            for attr_field in fields(self)
        ]

    def to_dict(self) -> dict:
        return asdict(self)

    def __getitem__(self, key: str) -> str:
        return getattr(self, key)

    @property
    def OriginalROINames(self) -> List[str]:  # noqa N802
        return [roi.ROIName for roi in self.OriginalROIMeta]

    def __rich_repr__(self) -> Iterator[tuple[str, str | Sequence[str]]]:
        # for each key-value pair, 'yield key, value'
        for attr_field in fields(self):
            if attr_field.name.endswith("UID"):
                yield (
                    attr_field.name,
                    f"...{getattr(self, attr_field.name)[-10:]}",
                )
            else:
                yield attr_field.name, getattr(self, attr_field.name)

    # or 'key in RTSTRUCTMetadata' to check if a key exists
    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    # implement dict-like 'update' method
    def update(self, **kwargs: str) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


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
    ReferencedROINumber: int
    contour_geometric_type: str
    num_points: int
    slices: List[ContourSlice]

    def __str__(self) -> str:
        return (
            f"{self.name} (ROI#={self.ReferencedROINumber}) "
            f"{self.NumSlices} slices & {self.NumberOfContourPoints} points"
        )

    def __repr__(self) -> str:
        return (
            f"ROI<name={self.name}, ReferencedROINumber={self.ReferencedROINumber}, "
            f"num_slices={self.NumSlices}, num_points={self.NumberOfContourPoints}>"
        )

    def __len__(self) -> int:
        return len(self.slices)

    def __iter__(self) -> Iterator:
        return iter(self.slices)

    @property
    def NumSlices(self) -> int:  # noqa N802
        return len(self.slices)

    @property
    def NumberOfContourPoints(self) -> int:  # noqa N802
        return self.num_points

    @property
    def ContourGeometricType(self) -> str:  # noqa N802
        return self.contour_geometric_type

    def to_dict(self) -> dict:
        return asdict(self)
