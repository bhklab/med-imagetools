from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
    Mapping,
    TypeAlias,
)

import numpy as np
from pydicom.dataset import FileDataset

from imgtools.dicom import DicomInput, load_dicom
from imgtools.dicom.dicom_metadata import extract_metadata
from imgtools.exceptions import ROIContourError
from imgtools.loggers import logger

# from imgtools.utils import physical_points_to_idxs

if TYPE_CHECKING:
    from pydicom.dataset import FileDataset

# Define type aliases
"""Alias for a string or a list of strings used to represent selection patterns."""
SelectionPattern: TypeAlias = str | List[str] | List[List[str]]

"""Alias for ROI names, which can be:
- SelectionPattern:
    - A single string pattern.
    - A list of string patterns.
- A dictionary mapping strings to patterns or lists of patterns.
- None, to represent the absence of any selection.
"""
ROINamePatterns: TypeAlias = (
    SelectionPattern | Mapping[str, SelectionPattern] | None
)


class ROIExtractionErrorMsg(str):
    pass


class ContourGeometricType(str, Enum):
    """
    https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.8.8.6.html
    POINT: single point
    OPEN_PLANAR: open contour containing coplanar points
    OPEN_NONPLANAR: open contour containing non-coplanar points
    CLOSED_PLANAR: closed contour (polygon) containing coplanar points
    """

    POINT = "POINT"
    OPEN_PLANAR = "OPEN_PLANAR"
    OPEN_NONPLANAR = "OPEN_NONPLANAR"
    CLOSED_PLANAR = "CLOSED_PLANAR"

    def __str__(self) -> str:
        return self.value


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


@dataclass
class ROI:
    """Represents a region of interest (ROI), containing slices of contours."""

    name: str
    ReferencedROINumber: int
    num_points: int
    slices: List[ContourSlice] = field(repr=False)
    contour_geometric_type: ContourGeometricType | None = field(default=None)

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
    def ContourGeometricType(self) -> str | None:  # noqa N802
        return self.contour_geometric_type

    def to_dict(self) -> dict:
        return asdict(self)


class ContourPointsAcrossSlicesError(Exception):
    """Exception raised when contour points span across multiple slices."""

    def __init__(
        self,
        roi_name: str,
        contour_num: int,
        slice_points_shape: tuple,
        z_values: list,
    ) -> None:
        self.roi_name = roi_name
        self.contour_num = contour_num
        self.slice_points_shape = slice_points_shape
        self.z_values = z_values
        super().__init__(self._generate_message())

    def _generate_message(self) -> str:
        return (
            f"Contour points for ROI '{self.roi_name}' and contour {self.contour_num} "
            f"(shape: {self.slice_points_shape}) span across multiple slices: {self.z_values}."
        )


@dataclass
class RTStructureSet:
    """Represents the entire structure set, containing multiple ROIs."""

    # these are the EXTRACTED ROI names, not the original ones in the RTSTRUCT
    # since some will fail to extract
    roi_names: List[str]
    metadata: dict[str, Any] = field(repr=False)
    roi_map: dict[str, ROI] = field(repr=False)

    roi_map_errors: dict[str, ROIExtractionErrorMsg] = field(
        repr=False, default_factory=dict
    )

    @property
    def rois(self) -> dict[str, ROI]:
        return {
            roi_name: roi
            for roi_name, roi in self.roi_map.items()
            if isinstance(roi, ROI)
        }

    @classmethod
    def from_dicom(
        cls,
        dicom: DicomInput,
        suppress_warnings: bool = False,
        roi_name_pattern: str | None = None,
        ignore_case: bool = True,
    ) -> RTStructureSet:
        """Create a RTStructureSet object from an RTSTRUCT DICOM file.
        Parameters
        ----------
        dicom : str | Path | bytes | FileDataset
            The RTSTRUCT DICOM object.
        suppress_warnings : bool, optional
            Whether to suppress warnings when extracting ROI points.
            Default is False.
        roi_name_pattern : str, optional
            A regular expression pattern to match ROI names. Default is None.
        ignore_case : bool, optional
            If True, ignore case when matching ROI names. Default is True.
        Returns
        -------
        RTStructureSet
            The structure set data extracted from the RTSTRUCT.
        """
        logger.debug("Loading RTSTRUCT DICOM file.", dicom=dicom)
        dicom_rt: FileDataset = load_dicom(dicom)
        metadata: Dict[str, Any] = extract_metadata(
            dicom_rt, "RTSTRUCT", extra_tags=None
        )

        case_ignore = (
            re.IGNORECASE if ignore_case else 0
        )  # for pattern matching

        # Create a dictionary to store the ROI objects
        roi_dict: dict[str, ROI] = {}
        roi_errors: dict[str, ROIExtractionErrorMsg] = {}
        extracted_rois = []  # only track successfully extracted ROIs

        # Extract ROI contour points for each ROI and
        for roi_index, roi_name in enumerate(metadata["ROINames"]):
            if roi_name_pattern and not re.match(
                roi_name_pattern, roi_name, flags=case_ignore
            ):
                continue
            try:
                extracted_roi = cls._get_roi_points(
                    dicom_rt, roi_index=roi_index, roi_name=roi_name
                )
            except ROIContourError as ae:
                if not suppress_warnings:
                    logger.warning(
                        f"Could not get points for ROI `{roi_name}`.",
                        rtstruct_series=metadata["SeriesInstanceUID"],
                        error=ae,
                    )
                error_string = f"Error extracting ROI '{roi_name}': {ae}"
                roi_errors[roi_name] = ROIExtractionErrorMsg(error_string)
            else:
                roi_dict[roi_name] = extracted_roi
                extracted_rois.append(roi_name)
        logger.debug(
            "Finished extracting ROI points.",
            extracted_rois=extracted_rois,
            failed_rois=list(roi_errors.keys()),
        )
        # Create a new RTStructureSet object
        structure_set = cls(
            roi_map=roi_dict,
            roi_names=extracted_rois,
            roi_map_errors=roi_errors,
            metadata=metadata,
        )
        return structure_set

    @staticmethod
    def _get_roi_points(
        rtstruct: FileDataset, roi_index: int, roi_name: str
    ) -> ROI:
        """Extract and reshapes contour points for a specific ROI in an RTSTRUCT file.
        The passed in roi_index is what is used to index the ROIContourSequence,
        whereas the roi_name is mainly used for debugging, and saved in the returned `ROI`
        instance.
        This method assumes that the order of the rois in dcm.StructureSetROISequence is
        the same order that you will find their corresponding contour data in
        dcm.ROIContourSequence.
        Parameters
        ----------
        rtstruct : FileDataset
            The loaded DICOM RTSTRUCT file.
        roi_index : int
            The index of the ROI in the ROIContourSequence.
        roi_name : str
            The name of the ROI to extract points for.
        Returns
        -------
        imgtools.modules.structureset.ROI (which is a container for List[np.ndarray])
            A list of numpy arrays where each array contains the 3D physical coordinates
            of the contour points for a specific slice.
        Raises
        ------
        ROIContourError
            If the ROIContourSequence, ContourSequence, or ContourData is missing or malformed.
        Examples
        --------
        >>> rtstruct = dcmread(
        ...     "path/to/rtstruct.dcm", force=True
        ... )
        >>> StructureSet._get_roi_points(rtstruct, 0, "GTV")
        """
        # Notes
        # -----
        # The structure of the contour data in the DICOM RTSTRUCT file is as follows:
        # > ROIContourSequence (3006, 0039)
        # >> ReferencedROINumber (3006, 0084)
        # >> ContourSequence (3006, 0040)
        # >>> ContourData (3006, 0050)
        # >>> ContourGeometricType (3006, 0042)
        # >>> NumberOfContourPoints (3006, 0046)

        # Check for ROIContourSequence
        if not hasattr(rtstruct, "ROIContourSequence"):
            raise ROIContourError(
                "The DICOM RTSTRUCT file is missing 'ROIContourSequence'."
            )
        # Check if ROI index exists in the sequence
        elif roi_index >= len(rtstruct.ROIContourSequence) or roi_index < 0:
            msg = (
                f"ROI index {roi_index} is out of bounds for the "
                f" 'ROIContourSequence' with length {len(rtstruct.ROIContourSequence)}."
            )
            raise ROIContourError(msg)

        roi_contour = rtstruct.ROIContourSequence[roi_index]

        # Check for ContourSequence in the specified ROI
        if not hasattr(roi_contour, "ContourSequence"):
            msg = (
                f"ROI at index {roi_index}, (ReferencedROINumber={roi_index + 1}) "
                "is missing 'ContourSequence';"
            )
            raise ROIContourError(msg)

        contour_sequence = roi_contour.ContourSequence

        # Check for ContourData in each contour
        contour_points = []
        total_num_points = 0
        contourgeometric_types = set()
        for i, slc in enumerate(contour_sequence):
            if not hasattr(slc, "ContourData"):
                msg = f"Contour {i} in ROI at index {roi_index} is missing 'ContourData'. "
                raise ROIContourError(msg)
            roi_points = np.array(slc.ContourData).reshape(-1, 3)
            contour_slice = ContourSlice(roi_points)
            contour_points.append(contour_slice)
            total_num_points += slc.get("NumberOfContourPoints", 0)
            contourgeometric_types.add(slc.get("ContourGeometricType", None))

        if len(contourgeometric_types) > 1:
            warnmsg = (
                f"Multiple ContourGeometricTypes found for ROI '{roi_name}': "
                f"{contourgeometric_types}."
            )
            logger.warning(warnmsg)
            cgt = ",".join(contourgeometric_types)
        else:
            cgt = contourgeometric_types.pop()

        return ROI(
            name=roi_name,
            ReferencedROINumber=int(roi_contour.ReferencedROINumber),
            contour_geometric_type=ContourGeometricType(cgt),
            num_points=total_num_points,
            slices=contour_points,
        )

    def summary(self) -> dict:
        """Return a comprehensive summary of the RTStructureSet."""

        roi_errors_info = {
            name: str(error) for name, error in self.roi_map_errors.items()
        }

        # ignore iroi names because we already have them in roi_map
        meta = {
            k: v for k, v in self.metadata.copy().items() if k != "ROINames"
        }

        return {
            "Metadata": meta,
            "ROI Details": list(self.roi_map.values()),
            "ROIErrors": roi_errors_info,
        }


if __name__ == "__main__":
    from rich import print

    p = Path(
        "/home/gpudual/bhklab/radiomics/Projects/med-imagetools/data/HNSCC/HNSCC-01-0176/RTSTRUCT_Series72843515/00000001.dcm"
    )

    # Read entire file
    rtstruct = RTStructureSet.from_dicom(p)
    print(rtstruct.summary())

    # only match *TV.*
    rtstruct = RTStructureSet.from_dicom(
        p, roi_name_pattern=".*TV.*", ignore_case=True
    )
    print(rtstruct.summary())
