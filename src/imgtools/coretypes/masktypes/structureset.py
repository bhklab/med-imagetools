from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
)

import numpy as np
from pydicom.dataset import Dataset, FileDataset
from pydicom.sequence import Sequence

from imgtools.dicom import DicomInput, load_dicom
from imgtools.dicom.dicom_metadata import extract_metadata
from imgtools.exceptions import (
    ContourPointsAcrossSlicesError,
    MissingROIError,
    ROIContourError,
)
from imgtools.loggers import logger

# from .roi_matching import (
#     ROI_MatchingType,
#     ROIMatcher,
#     handle_roi_matching,
#     match_roi,
# )

# from imgtools.utils import physical_points_to_idxs
if TYPE_CHECKING:
    from pydicom.dataset import FileDataset


class ROIExtractionErrorMsg(str):
    pass


@dataclass
class RTStructureSet:
    """Represents the entire structure set, containing multiple ROIs.

    Attributes
    ----------
    roi_names : List[str]
        List of ROI names extracted from the RTSTRUCT.
    metadata : dict[str, Any]
        Metadata extracted from the RTSTRUCT DICOM file.
    roi_map : dict[str, ROI]
        Dictionary mapping ROI names to their corresponding `ROI` objects.
    roi_map_errors : dict[str, ROIExtractionErrorMsg]
        Dictionary mapping ROI names to any extraction errors encountered.

    Methods
    -------
    from_dicom(dicom: DicomInput) -> RTStructureSet
        Create a `RTStructureSet` object from a DICOM file.
    match_roi(pattern: str, ignore_case: bool = True) -> List[str] | None
        Search for ROI names matching a given pattern.
    __getitem__(idx: str | int | slice) -> ROI | List[ROI]
        Access ROI objects by name, index, or slice.
    summary() -> dict
        Return a comprehensive summary of the RTStructureSet.
    """

    # these are the EXTRACTED ROI names, not the original ones in the RTSTRUCT
    # since some will fail to extract
    metadata: dict[str, Any] = field(repr=False)
    roi_names: List[str] = field(
        default_factory=list,
        init=False,
    )
    roi_map: dict[str, Sequence] = field(
        repr=False,
        default_factory=dict,
    )
    roi_map_errors: dict[str, ROIExtractionErrorMsg] = field(
        repr=False, default_factory=dict, init=False
    )

    @classmethod
    def from_dicom(
        cls,
        dicom: DicomInput,
        suppress_warnings: bool = False,
    ) -> RTStructureSet:
        """Create a RTStructureSet object from an RTSTRUCT DICOM file.

        Lazy loads by default, by giving access to ROI Names and metadata
        and then loads the ROIs on demand. See Notes.

        Parameters
        ----------
        dicom : str | Path | bytes | FileDataset
            The RTSTRUCT DICOM object.
        suppress_warnings : bool, optional
            Whether to suppress warnings when extracting ROI points.
            Default is False.
        Returns
        -------
        RTStructureSet
            The structure set data extracted from the RTSTRUCT.

        Notes
        -----
        Compared to the old implementation, we dont extract the numpy arrays
        for the ROIs immediately. Instead, we just extract the metadata and
        then store the weak-refs to the `ROIContourSequence` objects.
        This allows us to avoid the computation of the numpy arrays until we
        actually ask for them (i.e converting to `sitk.Image`) which might
        use some regex pattern matching to only process the ROIs that
        we want.
        """
        logger.debug("Loading RTSTRUCT DICOM file.", dicom=dicom)
        dicom_rt: FileDataset = load_dicom(dicom)
        metadata: Dict[str, Any] = extract_metadata(
            dicom_rt, "RTSTRUCT", extra_tags=None
        )
        rt = cls(
            metadata=metadata,
        )
        rt.roi_names.extend(metadata["ROINames"])

        # Extract ROI contour points for each ROI and
        for roi_index, roi_name in enumerate(metadata["ROINames"]):
            try:
                extracted_roi: Sequence = cls._get_roi_points(
                    dicom_rt, roi_index=roi_index
                )
            except ROIContourError as ae:
                if not suppress_warnings:
                    logger.warning(
                        f"Could not get points for ROI `{roi_name}`.",
                        rtstruct_series=metadata["SeriesInstanceUID"],
                        error=ae,
                    )
                error_string = f"Error extracting ROI '{roi_name}': {ae}"
                rt.roi_map_errors[roi_name] = ROIExtractionErrorMsg(
                    error_string
                )
            else:
                rt.roi_map[roi_name] = extracted_roi
                rt.roi_names.append(roi_name)

        return rt

    @staticmethod
    def _get_roi_points(rtstruct: FileDataset, roi_index: int) -> Sequence:
        """Extract and reshapes contour points for a specific ROI in an RTSTRUCT file.
        The passed in roi_index is what is used to index the ROIContourSequence,
        whereas the roi_name is mainly used for debugging purposes.


        This method assumes that the order of the rois in dcm.StructureSetROISequence is
        the same order that you will find their corresponding contour data in
        dcm.ROIContourSequence.

        Parameters
        ----------
        rtstruct : FileDataset
            The loaded DICOM RTSTRUCT file.
        roi_index : int
            The index of the ROI in the ROIContourSequence.

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

        # Check for ContourSequence in the specified ROI
        if not hasattr(
            roi_contour := rtstruct.ROIContourSequence[roi_index],
            "ContourSequence",
        ):
            msg = (
                f"ROI at index {roi_index}, (ReferencedROINumber={roi_index + 1}) "
                "is missing 'ContourSequence';"
            )
            raise ROIContourError(msg)

        return roi_contour.ContourSequence

        # # Check for ContourData in each contour
        # contour_sequence = roi_contour.ContourSequence

        # contour_slices = []
        # total_num_points = 0
        # for i, slc in enumerate(contour_sequence):
        #     if not hasattr(slc, "ContourData"):
        #         msg = f"Contour {i} in ROI at index {roi_index} is missing 'ContourData'. "
        #         raise ROIContourError(msg)

        #     roi_points = np.array(slc.ContourData).reshape(-1, 3)
        # contour_slices.append(ContourSlice(roi_points))
        # total_num_points += slc.get("NumberOfContourPoints", 0)
        # cgt = slc.get("ContourGeometricType", None)

        # return ROI(
        #     name=roi_name,
        #     ReferencedROINumber=int(roi_contour.ReferencedROINumber),
        #     num_points=total_num_points,
        #     slices=contour_slices,
        # )

    def __getitem__(self, idx: str | int | slice) -> Sequence | List[Sequence]:
        """Extend slice based access to the data in the RTStructureSet
        rtss = RTStructureSet.from_dicom(...)
        - rtss['GTV'] -> ROI instance
            if key exists EXACTLY as 'GTV' in the self.rois dict, return the `ROI` instance
            representing the contour points (sinlge ROI element)
            (maybe we should be returning as a LIST of only 1 element?)
        - rtss[0] -> ROI instance
            if key is an integer, return the `ROI` instance at that index
        - rtss[0:2] -> List[ROI] instance
        """
        match idx:
            case int():
                # Return the ROI at the specified index
                return self.roi_map[self.roi_names[idx]]
            case slice():
                # Return a list of ROIs for the specified slice
                return [self.roi_map[name] for name in self.roi_names[idx]]
            case str():
                # Check if the name exists in the roi_names
                if idx in self.roi_names:
                    return self.roi_map[idx]
                else:
                    errmsg = (
                        f"Key `{idx}` not found in structure set's ROI names"
                    )
            case _:
                errmsg = (
                    f"Key `{idx}` of type {type(idx)} not supported. "
                    "Expected int, slice, or str."
                )
        raise MissingROIError(errmsg)

    def _ipython_key_completions_(self) -> list[str]:
        """IPython/Jupyter tab completion when indexing rtstruct[...]"""
        return self.roi_names

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
            "ROI Details": self.roi_map,
            "ROIErrors": roi_errors_info,
        }

    def __len__(self) -> int:
        return len(self.roi_names)


if __name__ == "__main__":
    from rich import print

    p = Path("data/HNSCC/HNSCC-01-0176/RTSTRUCT_Series72843515/00000001.dcm")

    # Read entire file
    rtstruct = RTStructureSet.from_dicom(p)
    print(rtstruct.summary())

    # print(f"{rtstruct.match_roi(".*TV.*", ignore_case=True)=}")


# class ContourGeometricType(str, Enum):
#     """
#     https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.8.8.6.html
#     POINT: single point
#     OPEN_PLANAR: open contour containing coplanar points
#     OPEN_NONPLANAR: open contour containing non-coplanar points????
#     CLOSED_PLANAR: closed contour (polygon) containing coplanar points
#     """

#     POINT = "POINT"
#     OPEN_PLANAR = "OPEN_PLANAR"
#     OPEN_NONPLANAR = "OPEN_NONPLANAR"
#     CLOSED_PLANAR = "CLOSED_PLANAR"

#     def __str__(self) -> str:
#         return self.value


# class ContourSlice(np.ndarray):
#     """Represents the contour points for a single slice.
#     Simply a NumPy array with shape (n_points, 3) where the last dimension
#     represents the x, y, and z coordinates of each point.
#     Examples
#     --------
#     So if the slice has points representing a square in the x-y plane, the
#     array would look like this:
#     ```python
#     >>> ContourSlice(
#             [
#                 [0, 0, 0],
#                 [1, 0, 0],
#                 [1, 1, 0],
#                 [0, 1, 0],
#                 [0, 0, 0],
#             ]
#         )
#     ```
#     """

#     def __new__(cls, input_array: np.ndarray) -> ContourSlice:
#         obj = np.asarray(input_array).view(cls)
#         return obj

#     def __array_finalize__(self, obj: np.ndarray | None) -> None:
#         if obj is None:
#             return
#         assert self.ndim == 2
#         assert self.shape[1] == 3

#     def __array_wrap__(
#         self,
#         out_arr: np.ndarray,
#         context: tuple[np.ufunc, tuple[Any, ...], int] | None = None,  # noqa
#         subok: bool = True,
#     ) -> np.ndarray | ContourSlice:
#         """Ensure output retains ContourSlice type if shape is valid.
#         When performing operations on a ContourSlice, the output shape could be
#         altered. This method ensures that the output retains the ContourSlice type
#         if the shape is still valid.
#         Examples
#         --------
#         ```python
#         >>> contour = ContourSlice([[0, 0, 0], [1, 1, 1]])
#         >>> contour + 1
#         ContourSlice<points.shape=(2, 3)>
#         ```
#         ```python
#         >>> contour = ContourSlice([[0, 0, 0], [1, 1, 1]])
#         >>> contour.mean(axis=0)
#         array([0.5, 0.5, 0.5])
#         ```
#         """
#         if out_arr.ndim == 2 and out_arr.shape[1] == 3:
#             return out_arr.view(ContourSlice)  # Preserve type
#         # Return as NumPy array if shape changes # Return as a NumPy array if shape is altered
#         return out_arr

#     def __repr__(self) -> str:
#         return f"ContourSlice<points.shape={self.shape}>"
