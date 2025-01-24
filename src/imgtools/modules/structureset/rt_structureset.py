from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, List

import numpy as np

from imgtools.exceptions import MissingROIError, ROIContourError
from imgtools.logging import logger
from imgtools.modules.structureset import (
    ROI,
    ContourSlice,
    DicomInput,
    RTSTRUCTMetadata,
    extract_rtstruct_metadata,
    load_rtstruct_dcm,
)

if TYPE_CHECKING:
    from pydicom.dataset import FileDataset


@dataclass
class RTStructureSet:
    """Represents the entire structure set, containing multiple ROIs."""

    rois: dict[str, ROI] = field(repr=False)
    metadata: RTSTRUCTMetadata

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
            Whether to suppress warnings when extracting ROI points. Default is False.
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
        dicom_rt = load_rtstruct_dcm(dicom)
        metadata = extract_rtstruct_metadata(dicom_rt)

        case_ignore = re.IGNORECASE if ignore_case else 0  # for pattern matching

        # Create a dictionary to store the ROI objects
        roi_dict: dict[str, ROI] = {}

        # Extract ROI contour points for each ROI and
        for roi_index, roi_name in enumerate(metadata["OriginalROINames"]):
            if roi_name_pattern and not re.match(roi_name_pattern, roi_name, flags=case_ignore):
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
            else:
                roi_dict[roi_name] = extracted_roi

        metadata.ExtractedNumberOfROIs = len(roi_dict)
        metadata.ExtractedROINames = list(roi_dict.keys())
        # Create a new RTStructureSet object
        structure_set = cls(rois=roi_dict, metadata=metadata)

        return structure_set

    @property
    def roi_names(self) -> List[str]:
        """Get a list of all ROI names in the structure set."""
        return list(self.rois.keys())

    def match_roi(self, pattern: str, ignore_case: bool = True) -> List[str] | None:
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
        >>> structure_set = RTStructureSet.from_dicom(
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

    def __getitem__(self, name: str) -> list[ROI] | str:
        """Retrieve an ROI by name or access the metadata"""
        if name in self.rois:
            return [self.rois[name]]

        # Check if name is a pattern and match against ROI names
        if matched_rois := self.match_roi(name):
            return [self.rois[roi] for roi in matched_rois]
        elif self.metadata:
            if name in self.metadata:
                return getattr(self.metadata, name)
            else:
                msg = f"{name} not found in ROI names OR metadata."
                msg += f" Available ROIs: {self.roi_names}"
                msg += f" Available metadata: {self.metadata.keys()}"
                raise MissingROIError(msg)
        else:
            errmsg = f"Key `{name}` not found in structure set's ROI names or metadata."
            raise MissingROIError(errmsg)

    def __rich_repr__(self) -> Iterator:
        yield "rois", len(self.rois)
        yield "Metadata", self.metadata

    def __len__(self) -> int:
        return len(self.rois)

    def __iter__(self) -> Iterator[tuple[str, ROI]]:
        # return tuples of (name, ROI) for iteration
        return iter(self.rois.items())

    @staticmethod
    def _get_roi_points(rtstruct: FileDataset, roi_index: int, roi_name: str) -> ROI:
        """Extract and reshapes contour points for a specific ROI in an RTSTRUCT file.

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
                msg = (
                    f"Contour {i} in ROI at index {roi_index} is missing 'ContourData'. "
                    f"ContourGeometricType: {roi_contour.get("ContourGeometricType", "unknown")}."
                    f"NumberOfContourPoints: {roi_contour.get('NumberOfContourPoints', 'unknown')}"
                )
                raise ROIContourError(msg)
            roi_points = np.array(slc.ContourData).reshape(-1, 3)
            contour_slice = ContourSlice(roi_points)
            contour_points.append(contour_slice)

        return ROI(roi_name, roi_index, contour_points)


if __name__ == "__main__":
    import time
    from pathlib import Path

    import pandas as pd
    from rich import print

    index = Path(".imgtools/imgtools_data.csv")
    df = pd.read_csv(index, index_col=0)

    df = df[df["modality"] == "RTSTRUCT"]

    cols_of_interest = ["patient_ID", "file_path"]

    # subset the dataframe to only include the columns of interest
    df = df[cols_of_interest]

    for idx, row in df.iterrows():
        patient_id = row["patient_ID"]
        file_path = row["file_path"]

        start = time.time()
        rtstruct = RTStructureSet.from_dicom(
            file_path,
            suppress_warnings=True,
        )
        print(f"Time taken: {time.time() - start:.2f} seconds")
        print(rtstruct)

        print("_" * 80)
        print(rtstruct["PatientID"])
        print(rtstruct["SeriesInstanceUID"])
        print(rtstruct["gtv.*"])
        print(rtstruct["ctv.*"])

        # anything that has 'ptv' in the name
        print(rtstruct["ptv.*"])
        break

    # # Profile the main function
    # # with cProfile.Profile() as pr:
    # main()

    # # # Save profiling stats
    # # with open("profile_results.prof", "w") as f:
    # #     stats = pstats.Stats(pr, stream=f)
    # #     stats.sort_stats(pstats.SortKey.TIME)
    # #     stats.print_stats()

    # # vizualize the profiling stats with snakeviz

    # # !pip install snakeviz
