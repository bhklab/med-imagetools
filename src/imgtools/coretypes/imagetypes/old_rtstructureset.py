from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import TYPE_CHECKING, Any, Iterator, List, Sequence

import numpy as np
from pydicom.dataset import FileDataset

from imgtools.dicom import load_rtstruct_dcm, rtstruct_reference_uids
from imgtools.exceptions import (
    MissingROIError,
    ROIContourError,
    RTSTRUCTAttributeError,
)
from imgtools.logging import logger
from imgtools.utils import DataclassMixin

if TYPE_CHECKING:
    from pydicom import FileDataset


class ROIContourGeometricType(str, Enum):
    """Enum for the geometric types of ROI contours."""

    # https://dicom.nema.org/medical/Dicom/2018d/output/chtml/part03/sect_C.8.8.6.html#sect_C.8.8.6.1
    POINT = "POINT"
    OPEN_PLANAR = "OPEN_PLANAR"
    CLOSED_PLANAR = "CLOSED_PLANAR"
    OPEN_NONPLANAR = "OPEN_NONPLANAR"


@dataclass
class ROI(DataclassMixin):
    """Dataclass for ROI metadata.

    New keys can be added as needed.
    """

    ROIName: str
    ROINumber: str
    ReferencedFrameOfReferenceUID: str
    ContourGeometricType: ROIContourGeometricType
    ROIDisplayColor: str | None = field(default=None)
    ROIGenerationAlgorithm: str | None = field(default=None)
    NumberOfContourPoints: int = field(default=0)
    ContourData: List[ContourSlice] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.ContourData)

    def __iter__(self) -> Iterator:
        return iter(self.ContourData)

    def __rich_repr__(self) -> Iterator[tuple[str, str | Sequence[str]]]:
        for attr_field, value in super().__rich_repr__():
            if attr_field == "ContourData":
                ystr = f"<NumSlices={len(self.ContourData)}>"
                yield attr_field, ystr
            else:
                yield attr_field, value


def _roimetadata_from_dicom(rtstruct: FileDataset) -> List[ROI]:
    """Create an ROIMetadata object from a DICOM dataset."""

    roi_mapping: defaultdict[str, Any] = defaultdict()

    for contour_meta in rtstruct.StructureSetROISequence:
        roi_mapping[contour_meta.ROINumber] = contour_meta

    if not hasattr(rtstruct, "ROIContourSequence"):
        errmsg = "The DICOM RTSTRUCT file is missing 'ROIContourSequence'."
        raise ROIContourError(errmsg)
    elif len(roi_mapping) != len(rtstruct.ROIContourSequence):
        found = len(rtstruct.ROIContourSequence)
        exp = len(roi_mapping)
        errmsg = f"ROI count mismatch: {found} in file vs {exp} expected."
        raise RTSTRUCTAttributeError(errmsg)

    rois: list[ROI] = []

    for contour_seq in rtstruct.ROIContourSequence:
        if (meta := roi_mapping.get(contour_seq.ReferencedROINumber)) is None:
            # something really went wrong...
            msg = f"Referenced ROI number {contour_seq.ReferencedROINumber} not found."
            raise MissingROIError(msg)

        roi: defaultdict[str, str | None] = defaultdict()

        geometric_types = set()
        contour_slices = []
        total_points = 0

        if not hasattr(contour_seq, "ContourSequence"):
            msg = f"ContourSequence not found for ROI '{roi['ROIName']}' (#{roi['ROINumber']})."
            raise ROIContourError(msg)

        for slc in contour_seq.ContourSequence:
            if not hasattr(slc, "ContourData"):
                msg = f"ContourData not found for ROI '{roi['ROIName']}' (#{roi['ROINumber']})."
                raise ROIContourError(msg)

            _roi_points = np.array(slc.ContourData).reshape(-1, 3)
            contourslc = ContourSlice(_roi_points)

            geometric_types.add(slc.get("ContourGeometricType", None))

            contour_slices.append(contourslc)
            total_points += slc.get("NumberOfContourPoints", 0)

        if len(geometric_types) > 1:
            msg = (
                "Multiple geometric types found for"
                f" ROI '{roi['ROIName']}' (#{roi['ROINumber']})."
            )
            logger.warning(msg)

        rois.append(
            ROI(
                ROIName=meta.ROIName,
                ROINumber=meta.ROINumber,
                ReferencedFrameOfReferenceUID=meta.ReferencedFrameOfReferenceUID,
                ContourGeometricType=ROIContourGeometricType(
                    geometric_types.pop()
                ),
                ROIGenerationAlgorithm=contour_seq.get(
                    "ROIGenerationAlgorithm", None
                ),
                ROIDisplayColor=contour_seq.get("ROIDisplayColor", None),
                ContourData=contour_slices,
                NumberOfContourPoints=total_points,
            )
        )

    return rois


@dataclass
class RTSTRUCTMetadata(DataclassMixin):
    """Dataclass for RTSTRUCT metadata.

    New keys can be added as needed.
    """

    PatientID: str
    Modality: str
    StudyInstanceUID: str
    SeriesInstanceUID: str
    ReferencedStudyInstanceUID: str
    ReferencedSeriesInstanceUID: str
    OriginalROIs: List[ROI]
    OriginalNumberOfROIs: int

    @property
    def ROINames(self) -> List[str]:  # noqa N802
        return [roi.ROIName for roi in self.OriginalROIs]

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

    @classmethod
    def from_dicom(cls, dataset: FileDataset) -> RTSTRUCTMetadata:
        """Create an RTSTRUCTMetadata object from a DICOM dataset."""

        rtstruct: FileDataset = load_rtstruct_dcm(dataset)
        refseries, refstudy = rtstruct_reference_uids(rtstruct)
        _roi_meta: List[ROI] = _roimetadata_from_dicom(rtstruct)
        return cls(
            PatientID=dataset.PatientID,
            Modality=dataset.Modality,
            StudyInstanceUID=dataset.StudyInstanceUID,
            SeriesInstanceUID=dataset.SeriesInstanceUID,
            ReferencedStudyInstanceUID=refstudy,
            ReferencedSeriesInstanceUID=refseries,
            OriginalROIs=_roi_meta,
            OriginalNumberOfROIs=len(_roi_meta),
        )


class ContourSlice(np.ndarray):
    """Represents the contour points for a single slice.
    Simply a NumPy array with shape (n_points, 3) where the last dimension
    represents the x, y, and z coordinates of each point.

    Examples
    --------
    So if the slice has points representing a square in the x-y plane, the
    array would look like this:

    ```python
    >>> ContourSlice(
            [
                [0, 0, 0],
                [1, 0, 0],
                [1, 1, 0],
                [0, 1, 0],
                [0, 0, 0],
            ]
        )
    ```
    """

    def __new__(cls, input_array: np.ndarray) -> ContourSlice:
        obj = np.asarray(input_array).view(cls)
        return obj

    def __array_finalize__(self, obj: np.ndarray | None) -> None:
        if obj is None:
            return
        assert self.ndim == 2
        assert self.shape[1] == 3

    def __array_wrap__(
        self,
        out_arr: np.ndarray,
        context: tuple[np.ufunc, tuple[Any, ...], int] | None = None,  # noqa
        subok: bool = True,
    ) -> np.ndarray | ContourSlice:
        """Ensure output retains ContourSlice type if shape is valid.

        When performing operations on a ContourSlice, the output shape could be
        altered. This method ensures that the output retains the ContourSlice type
        if the shape is still valid.

        Examples
        --------
        ```python
        >>> contour = ContourSlice([[0, 0, 0], [1, 1, 1]])
        >>> contour + 1
        ContourSlice<points.shape=(2, 3)>
        ```

        ```python
        >>> contour = ContourSlice([[0, 0, 0], [1, 1, 1]])
        >>> contour.mean(axis=0)
        array([0.5, 0.5, 0.5])
        ```
        """
        if out_arr.ndim == 2 and out_arr.shape[1] == 3:
            return out_arr.view(ContourSlice)  # Preserve type
        # Return as NumPy array if shape changes # Return as a NumPy array if shape is altered
        return out_arr

    def __repr__(self) -> str:
        return f"ContourSlice<points.shape={self.shape}>"


if __name__ == "__main__":  # pragma: no cover
    from rich import print  # noqa
    import pandas as pd
    from tqdm import tqdm

    # rtp = "data/4D-Lung/113_HM10395/2.25.186899387610254289948150314209581209847.5/00000001.dcm"
    imgtools_file = ".imgtools/imgtools_data.csv"
    df = pd.read_csv(imgtools_file)
    rt_df = df[df["modality"] == "RTSTRUCT"]

    rtp = rt_df["file_path"].values[0]

    rtmeta = RTSTRUCTMetadata.from_dicom(load_rtstruct_dcm(rtp))
    print(rtmeta)
    exit()
    for rtp in tqdm(rt_df["file_path"].values):
        rtmeta = RTSTRUCTMetadata.from_dicom(load_rtstruct_dcm(rtp))
        # print(rtmeta)
        # print("*" * 80)
        # print("*" * 80)
        # print("*" * 80)
