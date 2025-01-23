from __future__ import annotations

import re
from typing import TYPE_CHECKING, Iterator, List

import numpy as np

from imgtools.logging import logger
from imgtools.modules.structureset import (
    ROI,
    RTSTRUCTMetadata,
    extract_rtstruct_metadata,
    load_rtstruct_dcm,
)

if TYPE_CHECKING:
    from pydicom.dataset import FileDataset


class MissingROIError(KeyError):
    """Custom exception for missing ROI in the structure set."""

    pass


class ROIContourError(Exception):
    """Custom exception for missing ROI contour data in the RTSTRUCT file."""

    pass


class StructureSetData:
    """Represents the entire structure set, containing multiple ROIs."""

    rois: dict[str, ROI]
    metadata: RTSTRUCTMetadata | None

    def __init__(
        self, rois: dict[str, ROI] | None = None, metadata: RTSTRUCTMetadata | None = None
    ) -> None:
        self.rois = rois or {}
        self.metadata = metadata

    def add_roi(self, name: str, slice_points: List[np.ndarray]) -> None:
        """Add a new ROI to the structure set or append slices to an existing ROI."""
        if name not in self.rois:
            self.rois[name] = ROI(name)

        # Add each slice to the ROI, will be converted to ContourSlice objects
        for points in slice_points:
            self.rois[name].add_slice(points)

    @property
    def roi_names(self) -> List[str]:
        """Get a list of all ROI names in the structure set."""
        return list(self.rois.keys())

    def match_roi(self, pattern: str, ignore_case: bool = False) -> List[str] | None:
        """Search for ROI names in self.roi_names based on a regular expression pattern.

        Parameters
        ----------
        pattern : str
            The regular expression pattern to search for.
        ignore_case : bool, optional
            Whether to ignore case in the regular expression matching. Default is False.

        Returns
        -------
        List[str] | None
            A list of matching ROI names if any match, None otherwise.

        Examples
        --------
        Assume the following rt has the roi names: ['GTV1', 'GTV2', 'PTV', 'CTV_0', 'CTV_1']
        >>> structure_set = StructureSetData.from_dicom(
        ...     "path/to/rtstruct.dcm"
        ... )
        >>> structure_set.match_roi("GTV.*")
        ['GTV1', 'GTV2']
        >>> structure_set.match_roi("ctv.*", ignore_case=True)
        ['CTV_0', 'CTV_1']
        """
        _flags = re.IGNORECASE if ignore_case else 0
        matches = [name for name in self.roi_names if re.fullmatch(pattern, name, flags=_flags)]
        return matches if matches else None

    def __getitem__(self, name: str) -> ROI:
        """Retrieve an ROI by name or access the metadata"""
        if name in self.rois:
            return self.rois[name]
        elif self.metadata:
            if name in self.metadata:
                return getattr(self.metadata, name)
            else:
                msg = f"{name} not found in ROI names OR metadata."
                msg += f" Available ROIs: {self.roi_names}"
                msg += f" Available metadata: {self.metadata.keys()}"
                raise MissingROIError(msg)
        else:
            errmsg = f"ROI `{name}` not found in the structure set."
            raise MissingROIError(errmsg)

    def __repr__(self) -> str:
        # roi_info = "\n\t".join(f"{name} ({len(roi)} slices)" for name, roi in self.rois.items())
        roi_info = f"ROIs: {len(self.rois)}"
        base_str = f"StructureSetData:\n\t{roi_info}\n"
        # newline for each key-value pair
        if self.metadata:
            metadata_str = "\n\t".join(f"{key}: {value}" for key, value in self.metadata.items())
            base_str += f"Metadata:\n\t{metadata_str}"
        return base_str

    def __len__(self) -> int:
        return len(self.rois)

    def __iter__(self) -> Iterator[tuple[str, ROI]]:
        # return tuples of (name, ROI) for iteration
        return iter(self.rois.items())

    @classmethod
    def from_dicom(
        cls,
        dicom: str | Path | bytes,
        suppress_warnings: bool = False,
        roi_name_pattern: str | None = None,
    ) -> StructureSetData:
        """Create a StructureSetData object from an RTSTRUCT DICOM file.

        Parameters
        ----------
        rtstruct : RTSTRUCTMetadata
            Metadata extracted from the RTSTRUCT file.
        dicom : str | Path | bytes
            The RTSTRUCT DICOM object.

        Returns
        -------
        StructureSetData
            The structure set data extracted from the RTSTRUCT.
        """
        structure_set = cls()
        dicom_rt = load_rtstruct_dcm(dicom)
        structure_set.metadata = extract_rtstruct_metadata(dicom_rt)

        # Extract ROI contour points for each ROI
        for roi_index, roi_name in enumerate(structure_set.metadata["OriginalROINames"]):
            if roi_name_pattern and not re.match(roi_name_pattern, roi_name):
                continue
            try:
                roi_points = cls._get_roi_points(dicom_rt, roi_index=roi_index)
            except ROIContourError as ae:
                if not suppress_warnings:
                    logger.warning(
                        f"Could not get points for ROI `{roi_name}`.",
                        rtstruct_series=structure_set["SeriesInstanceUID"],
                        error=ae,
                    )
            else:
                structure_set.add_roi(roi_name, roi_points)

        return structure_set

    @staticmethod
    def _get_roi_points(rtstruct: FileDataset, roi_index: int) -> List[np.ndarray]:
        """Extract and reshapes contour points for a specific ROI in an RTSTRUCT file.

        Parameters
        ----------
        rtstruct : FileDataset
            The loaded DICOM RTSTRUCT file.
        roi_index : int
            The index of the ROI in the ROIContourSequence.

        Returns
        -------
        List[np.ndarray]
            A list of numpy arrays where each array contains the 3D physical coordinates
            of the contour points for a specific slice.

        Raises
        ------
        ROIContourError
            If the ROIContourSequence, ContourSequence, or ContourData is missing or malformed.

        Examples
        --------
        >>> rtstruct = dcmread("path/to/rtstruct.dcm", force=True)
        >>> StructureSet._get_roi_points(rtstruct, 0)

        Notes
        -----
        The structure of the contour data in the DICOM RTSTRUCT file is as follows:
        > ROIContourSequence (3006, 0039)
        >> ReferencedROINumber (3006, 0084)
        >> ContourSequence (3006, 0040)
        >>> ContourData (3006, 0050)
        >>> ContourGeometricType (3006, 0042)
        >>> NumberOfContourPoints (3006, 0046)
        """
        # Check for ROIContourSequence
        if not hasattr(rtstruct, "ROIContourSequence"):
            raise ROIContourError("The DICOM RTSTRUCT file is missing 'ROIContourSequence'.")

        # Check if ROI index exists in the sequence
        if roi_index >= len(rtstruct.ROIContourSequence) or roi_index < 0:
            msg = (
                f"ROI index {roi_index} is out of bounds for the "
                f" 'ROIContourSequence' with length {len(rtstruct.ROIContourSequence)}."
            )
            raise ROIContourError(msg)

        roi_contour = rtstruct.ROIContourSequence[roi_index]

        # Check for ContourSequence in the specified ROI
        if not hasattr(roi_contour, "ContourSequence"):
            msg = f"ROI at index {roi_index} is missing 'ContourSequence';"
            raise ROIContourError(msg)

        contour_sequence = roi_contour.ContourSequence

        # Check for ContourData in each contour
        contour_points = []
        for i, slc in enumerate(contour_sequence):
            if not hasattr(slc, "ContourData"):
                _contour_type = roi_contour.get("ContourGeometricType", "unknown")
                msg = f"Contour {i} in ROI at index {roi_index} is missing 'ContourData'."
                msg += f"ContourGeometricType: {_contour_type}."
                raise ROIContourError(msg)
            contour_points.append(np.array(slc.ContourData).reshape(-1, 3))

        return contour_points


if __name__ == "__main__":
    from pathlib import Path

    data = Path("/home/bioinf/bhklab/radiomics/repos/med-imagetools/data")

    ct_dir = (
        data
        / "Head-Neck-PET-CT/HN-CHUS-052/08-27-1885-CA ORL FDG TEP POS TX-94629/3.000000-Merged-06362,"
    )
    rt_path = (
        data
        / "Head-Neck-PET-CT/HN-CHUS-052/08-27-1885-OrophCB.0OrophCBTRTID derived StudyInstanceUID.-94629/Pinnacle POI-41418/1-1.dcm"
    )

    rt = StructureSetData.from_dicom(rt_path, suppress_warnings=False)
    print(rt)
