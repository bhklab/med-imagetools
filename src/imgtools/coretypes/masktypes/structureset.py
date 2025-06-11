from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
)

import numpy as np
import SimpleITK as sitk
from pydicom.dataset import FileDataset
from skimage.draw import polygon2mask

from imgtools.coretypes.base_masks import ROIMaskMapping, VectorMask
from imgtools.coretypes.masktypes.roi_matching import (
    ROIMatchFailurePolicy,
    ROIMatchingError,
)
from imgtools.dicom import DicomInput, load_dicom
from imgtools.dicom.dicom_metadata import extract_metadata
from imgtools.exceptions import (
    MissingROIError,
    ROIContourError,
)
from imgtools.loggers import logger
from imgtools.utils import physical_points_to_idxs

if TYPE_CHECKING:
    from pydicom.dataset import FileDataset
    from pydicom.sequence import Sequence

    from imgtools.coretypes import MedImage
    from imgtools.coretypes.masktypes.roi_matching import (
        ROIMatcher,
    )

__all__ = [
    "RTStructureSet",
    "ROIContourExtractionError",
    "ContourPointsAcrossSlicesError",
    "MaskArrayOutOfBoundsError",
    "UnexpectedContourPointsError",
    "NonIntegerZSliceIndexError",
]


class ContourPointsAcrossSlicesError(Exception):  # pragma: no cover
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


class MaskArrayOutOfBoundsError(Exception):  # pragma: no cover
    """Exception raised when a mask array index is out of bounds for the reference image."""

    def __init__(
        self,
        roi_name: str,
        contour_num: int,
        z_int: int,
        mask_shape: tuple,
        slice_points_shape: tuple,
        z_values: list,
        reference_image: MedImage,
    ) -> None:
        self.roi_name = roi_name
        self.contour_num = contour_num
        self.z_int = z_int
        self.mask_shape = mask_shape
        self.slice_points_shape = slice_points_shape
        self.z_values = z_values
        self.reference_image = reference_image
        super().__init__(self._generate_message())

    def _generate_message(self) -> str:
        return (
            f"Z-index {self.z_int} is out of bounds for mask array "
            f"with shape {self.mask_shape}. "
            f"ROI: {self.roi_name}, "
            f"ContourNum: {self.contour_num}, "
            f"ContourPoints: {self.slice_points_shape}, "
            f"ZValues: {self.z_values}, "
            f"reference image geometry: {self.reference_image.geometry}"
        )


class UnexpectedContourPointsError(Exception):  # pragma: no cover
    """Exception raised when contour points have an unexpected structure."""

    def __init__(
        self,
        roi_name: str,
        contour_num: int,
        z_values: list,
    ) -> None:
        self.roi_name = roi_name
        self.contour_num = contour_num
        self.z_values = z_values
        super().__init__(self._generate_message())

    def _generate_message(self) -> str:
        return (
            f"Unexpected contour point structure for ROI '{self.roi_name}', "
            f"contour {self.contour_num}. Z-values: {self.z_values}"
        )


class NonIntegerZSliceIndexError(Exception):  # pragma: no cover
    """Exception raised when the Z-slice index is not an integer."""

    def __init__(self, roi_name: str, contour_num: int, z_idx: float) -> None:
        self.roi_name = roi_name
        self.contour_num = contour_num
        self.z_idx = z_idx
        super().__init__(self._generate_message())

    def _generate_message(self) -> str:
        return (
            f"Z-slice index {self.z_idx} is not an integer for ROI "
            f"'{self.roi_name}' and contour {self.contour_num} "
            "this could be because continuous in get_mask_ndarray() was set to True."
        )


class ROIContourExtractionError(ROIContourError):
    """Exception raised when extracting ROI contour data fails with details about the specific ROI.

    This exception contains additional information about the ROI index, name,
    and referenced ROI number to provide context for the error.
    """

    roi_index: int
    roi_name: str
    referenced_roi_number: int | None
    additional_info: dict | None
    message: str

    def __init__(
        self,
        message: str,
        roi_index: int,
        roi_name: str,
        referenced_roi_number: int | None = None,
        additional_info: dict | None = None,
    ) -> None:
        """Initialize with detailed information about the ROI extraction failure.

        Parameters
        ----------
        message : str
            Base error message describing what went wrong
        roi_index : int
            Index of the ROI in the ROIContourSequence
        roi_name : str
            Name of the ROI (for context in error messages)
        referenced_roi_number : int, optional
            Referenced ROI number from the DICOM file, by default None
        additional_info : dict, optional
            Any additional information to include in the error message, by default None
        """
        self.roi_index = roi_index
        self.roi_name = roi_name
        self.referenced_roi_number = referenced_roi_number or (roi_index + 1)
        self.additional_info = additional_info or {}

        # Build detailed error message
        roi_identifier = (
            f"ROI at index {self.roi_index}, "
            f"(ReferencedROINumber={self.referenced_roi_number})"
            f" with name '{self.roi_name}'"
        )
        detailed_message = f"{roi_identifier}: {message}"

        # Add any additional info to the message
        if self.additional_info:
            details = ", ".join(
                f"{k}={v}" for k, v in self.additional_info.items()
            )
            detailed_message += f" [Additional info: {details}]"

        super().__init__(detailed_message)


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
    """

    # these are the EXTRACTED ROI names, not the original ones in the RTSTRUCT
    # since some will fail to extract
    metadata: dict[str, Any] = field(repr=False)
    roi_names: List[str] = field(
        default_factory=list,
        init=False,
    )
    roi_map: dict[str, Sequence] = field(
        default_factory=dict,
    )
    roi_map_errors: dict[str, ROIContourError] = field(
        default_factory=dict,
        init=False,
    )

    # store a hidden cache to store the numpy arrays
    # after the first time we access them
    _roi_cache: dict[str, np.ndarray] = field(
        repr=False,
        default_factory=dict,
        init=False,
    )

    @property
    def plogger(self):  # type: ignore[no-untyped-def] # noqa
        """Return the logger for this class."""
        return self._logger

    @plogger.setter
    def plogger(self, logger):  # type: ignore[no-untyped-def] # noqa
        """Set the logger for this class."""
        self._logger = logger

    @classmethod
    def from_dicom(
        cls,
        dicom: DicomInput,
        metadata: Dict[str, Any] | None = None,
    ) -> RTStructureSet:
        """Create a RTStructureSet object from an RTSTRUCT DICOM file.

        Lazy loads by default, by giving access to ROI Names and metadata
        and then loads the ROIs on demand. See Notes.

        Parameters
        ----------
        dicom : str | Path | bytes | FileDataset
            - Either a path to the DICOM file, a directory containing
            *a single* DICOM file, or a `FileDataset` object.
            - If a directory is provided, it will be searched for a single DICOM
            file. If multiple files are found, an error will be raised.
            - If a `FileDataset` object is provided, it will be used directly.
        metadata : dict[str, Any] | None, optional
            If provided, this metadata will be used instead of extracting it
            from the DICOM file. This is useful because our crawler
            extracts and processes the metadata, possibly doing some better
            remapping to figure out the correct ReferencedSeriesInstanceUID.

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
        if isinstance(dicom, (str, Path)):
            dicom = Path(dicom)
            if dicom.is_dir():
                if len(list(dicom.glob("*.dcm"))) == 1:
                    dicom = list(dicom.glob("*.dcm"))[0]
                else:
                    errmsg = (
                        f"Directory `{dicom}` contains multiple DICOM files. "
                        f"Cannot determine which one to load."
                    )
                    raise ValueError(errmsg)

        # logger.debug("Loading RTSTRUCT DICOM file.", dicom=dicom)
        dicom_rt: FileDataset = load_dicom(dicom)
        metadata = metadata or extract_metadata(
            dicom_rt,
            "RTSTRUCT",
            extra_tags=None,
        )
        rt = cls(
            metadata={k: v for k, v in metadata.items() if v},
        )

        # Extract ROI contour points for each ROI and
        for roi_index, roi_name in enumerate(metadata["ROINames"]):  # type: ignore[arg-type]
            try:
                extracted_roi: Sequence = cls._get_roi_points(
                    dicom_rt,
                    roi_index=roi_index,
                    roi_name=roi_name,
                )
            except ROIContourError as ae:
                rt.roi_map_errors[roi_name] = ae
            else:
                rt.roi_map[roi_name] = extracted_roi
                rt.roi_names.append(roi_name)

        # tag the logger with the original RTSTRUCT file name
        rt.plogger = logger.bind(
            PatientID=metadata.get("PatientID", "Unknown"),
            SeriesInstanceUID=metadata.get("SeriesInstanceUID", "Unknown")[  # type: ignore[index]
                -8:
            ],
            filepath=Path(dicom) if isinstance(dicom, (str, Path)) else dicom,
        )
        return rt

    @staticmethod
    def _get_roi_points(
        rtstruct: FileDataset,
        roi_index: int,
        roi_name: str,
    ) -> Sequence:
        """Extract and reshapes contour points for a specific ROI in an RTSTRUCT file.
        The passed in roi_index is what is used to index the ROIContourSequence,
        whereas the roi_name is mainly used for debugging purposes.


        This method assumes that the order of the ROIs in dcm.StructureSetROISequence is
        the same order that you will find their corresponding contour data in
        dcm.ROIContourSequence.

        Parameters
        ----------
        rtstruct : FileDataset
            The loaded DICOM RTSTRUCT file.
        roi_index : int
            The index of the ROI in the ROIContourSequence.
        roi_name : str
            The name of the ROI, used for debugging and error messages only.

        Returns
        -------
        Sequence
            The contour points as the
            `rtstruct.ROIContourSequence[roi_index].ContourSequence`

        Raises
        ------
        ROIContourExtractionError
            If the ROIContourSequence, ContourSequence, or ContourData is
            missing or malformed.

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

        # Try to get ROIContour for this ROI
        roi_contour = rtstruct.ROIContourSequence[roi_index]

        # Set up the error with common info
        error = ROIContourExtractionError("", roi_index, roi_name)

        # Check for ContourSequence in the specified ROI
        if not hasattr(roi_contour, "ContourSequence"):
            error.message = "Missing 'ContourSequence'"
            raise error

        if len(roi_contour.ContourSequence) == 0:
            error.message = "Empty 'ContourSequence'"
            raise error

        # Sometimes the contour could be a POINT or just broken
        # and not have a ContourData
        # Check for ContourData in the first contour
        if not hasattr(roi_contour.ContourSequence[0], "ContourData"):
            error.message = "Missing 'ContourData' in ContourSequence"
            raise error

        # Check geometry type
        geometric_type = roi_contour.ContourSequence[0].ContourGeometricType
        if geometric_type != "CLOSED_PLANAR":
            error.message = f"Unexpected ContourGeometricType: {geometric_type}. Expected 'CLOSED_PLANAR'."
            error.additional_info = {"geometric_type": geometric_type}
            raise error

        return roi_contour.ContourSequence

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
            case int(pos) if 0 <= pos < len(self.roi_names):
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
                    f"Expected int 0 <= idx < {len(self.roi_names)}, "
                    f"slice, or str."
                )
        raise MissingROIError(errmsg)

    def get_mask_ndarray(
        self,
        reference_image: MedImage,
        roi_name: str,
        mask_img_size: tuple[int, int, int, int],
        continuous: bool = False,
    ) -> np.ndarray:
        """Get the mask as a numpy array for the specified ROI.

        Extracts & rasterizes the contour points for the specified ROI from
        the RTSTRUCT into a 3D binary, numpy array aligned with the reference
        image geometry.

        Internally, we convert the physical coordinates of each ROI's contours
        (stored in the `ROIContourSequence[roi_index].ContourSequence.ContourData`
        attribute) into pixel indices representing the boundaries of the
        contour using `physical_points_to_idxs` and then fill the mask
        using `skimage.draw.polygon2mask`.

        One key assumption here is that each 2D contour lies on a single axial slice.
        We raise explicit errors if we detect contours that span multiple slices or
        odd Z-index behavior, to be aligned with our assumptions.

        Parameters
        ----------
        reference_image : MedImage
            The reference image that defines the spatial geometry and metadata
            (e.g., direction, spacing, origin).
        roi_name : str
            Name of the ROI to extract.
        mask_img_size : tuple[int, int, int, int]
            Target shape of the binary mask, including depth (z), height (y), width (x),
            and number of channels (usually 1 here).
        continuous : bool, optional
            If True, use continuous interpolation for index conversion. This can lead to
            non-integer Z-slice indices, which will raise errors. Set to False (default)
            for safety.

        Returns
        -------
        np.ndarray
            3D binary mask with shape (Z, Y, X), where the ROI has value 1 and background 0.

        Raises
        ------
        ContourPointsAcrossSlicesError
            If a single contour spans multiple Z slices.
        MaskArrayOutOfBoundsError
            If a Z-index falls outside of expected image bounds.
        UnexpectedContourPointsError
            If Z-values are malformed or structurally unexpected.
        NonIntegerZSliceIndexError
            If continuous=True and Z-index is not an integer.
        """
        if roi_name in self._roi_cache:
            return self._roi_cache[roi_name]

        slices = [
            np.array(slc.ContourData).reshape(-1, 3)
            for slc in self.roi_map[roi_name]
        ]

        mask_points = physical_points_to_idxs(
            reference_image, slices, continuous=continuous
        )

        mask_array_3d = np.zeros(
            mask_img_size[0:3],
            dtype=np.uint8,
        )

        for contour_num, contour in enumerate(mask_points, start=0):
            # split the contour into z values and the points
            uniq_z_vals = list(np.unique(contour[:, 0]))
            slice_points = contour[:, 1:]

            # lets make sure that z is 1 unique value
            match uniq_z_vals:
                # make sure single z value is not negative
                case [z] if (z < 0) or (z >= mask_img_size[0]):
                    raise MaskArrayOutOfBoundsError(
                        roi_name,
                        contour_num,
                        z_int=z,
                        mask_shape=mask_img_size,
                        slice_points_shape=slice_points.shape,
                        z_values=uniq_z_vals,
                        reference_image=reference_image,
                    )
                case [z] if not float(z).is_integer():
                    raise NonIntegerZSliceIndexError(
                        roi_name,
                        contour_num,
                        z_idx=z,
                    )
                case [z] if len(uniq_z_vals) == 1:
                    z_idx = z
                case [*z_values]:
                    raise ContourPointsAcrossSlicesError(
                        roi_name,
                        contour_num,
                        slice_points.shape,
                        z_values,
                    )
                case _:
                    raise UnexpectedContourPointsError(
                        roi_name,
                        contour_num,
                        uniq_z_vals,
                    )

            filled_mask_array = polygon2mask(
                mask_img_size[1:3],
                slice_points,
            )

            mask_array_3d[z_idx, :, :] = np.logical_or(
                mask_array_3d[z_idx, :, :], filled_mask_array
            )

        # Store the mask in the cache
        self._roi_cache[roi_name] = mask_array_3d

        return mask_array_3d

    def get_vector_mask(
        self,
        reference_image: MedImage,
        roi_matcher: ROIMatcher,
    ) -> VectorMask | None:
        # ) -> tuple[sitk.Image | None, dict[int, ROIMaskMapping]]:
        """Contruct multi-channel (vector) mask using ROI matching.

        This function applies the given `ROIMatcher` to select ROIs and stack
        the resulting binary masks into a single 4D array (Z, Y, X, C), where C is
        the number of matched ROI keys. The logic is designed to be interpretable
        and efficient, avoiding full extraction until needed.

        Each ROI group is resolved according to the matching strategy in `ROIMatcher`.
        - MERGE: all matching ROIs are squashed into a single mask
        - KEEP_FIRST: only the first match is used
        - SEPARATE: each match becomes its own label (preferred for downstream tasks)

        We ensure that each voxel in the output mask belongs to at most one
        structure per channel.
        However, **we do not check for inter-channel overlap
        at this stage**—that responsibility is left to the caller.

        The returned image is a `sitk.Image` with vector pixel type (`sitk.sitkVectorUInt8`)
        and can be converted to our `VectorMask` class for further manipulation.

        Parameters
        ----------
        reference_image : MedImage
            The image whose geometry defines the spatial alignment of the masks.
        roi_matcher : ROIMatcher
            Matcher used to resolve user-defined keys to actual ROI names.

        Returns
        -------
        tuple[sitk.Image, dict[int, ROIMaskMapping]]
            A SimpleITK vector image containing all extracted ROIs in separate channels,
            and a dictionary mapping channel indices to `ROIMaskMapping`,
            a named tuple containing the roi_key and roi_names.

        Raises
        ------
        MissingROIError
            If no ROIs matched the specified patterns and the ROIMatchFailurePolicy is ERROR.

        Notes
        -----
        This method is designed to be the bridge between raw RTSTRUCT metadata
        and a usable segmentation mask, encoded in a vector-friendly format.
        Its companion class `VectorMask` offers high-level access to
        individual ROIs, label conversion, and overlap inspection.
        """
        matched_rois: list[tuple[str, list[str]]] = roi_matcher.match_rois(
            self.roi_names
        )

        # Handle the case where no matches were found, according to the policy
        if not matched_rois:
            message = "No ROIs matched any patterns in the match_map."
            match roi_matcher.on_missing_regex:
                case ROIMatchFailurePolicy.IGNORE:
                    # Silently return None
                    pass
                case ROIMatchFailurePolicy.WARN:
                    self.plogger.warning(
                        message,
                        roi_names=self.roi_names,
                        roi_matching=roi_matcher.match_map,
                    )
                case ROIMatchFailurePolicy.ERROR:
                    # Raise an error
                    errmsg = f"{message} Available ROIs: {self.roi_names}, "
                    raise ROIMatchingError(
                        errmsg,
                        roi_names=self.roi_names,
                        match_patterns=roi_matcher.match_map,
                    )
            return None

        self.plogger.debug("Matched ROIs", matched_rois=matched_rois)

        ref_size = reference_image.size
        mask_img_size: tuple[int, int, int, int] = (
            ref_size.depth,
            ref_size.height,
            ref_size.width,
            len(matched_rois),
        )

        mask_array_4d = np.zeros(
            mask_img_size,
            dtype=np.uint8,
        )

        # we need something to store the mapping
        # so that we can keep track of what the 3D mask matches to
        # the original roi name(s)
        mapping: dict[int, ROIMaskMapping] = {}

        for iroi, (roi_key, matches) in enumerate(matched_rois):
            self.plogger.debug(
                f"Processing {roi_key=} & {matches=} : ({iroi + 1}/{len(matched_rois)})",
            )
            match matches:
                case [*many_rois]:
                    # most likely handle type MERGE
                    for roi_name in many_rois:
                        mask_3d = self.get_mask_ndarray(
                            reference_image,
                            roi_name,
                            mask_img_size,
                            continuous=False,
                        )
                        # here we want to combine the masks in the same 4th dimension
                        mask_array_4d[:, :, :, iroi] = np.logical_or(
                            mask_array_4d[:, :, :, iroi], mask_3d
                        )
                    # image_id depends on the roi_matcher.handling_strategy
                    # if merging, image_id is just the key
                    # if separate, image_id is {roi_key}__[{roi_name}]
                    # if keeping first, image_id is {roi_key}__[{roi_name}]

                    mapping[iroi] = ROIMaskMapping(
                        roi_key=roi_key,
                        roi_names=many_rois,
                        image_id=roi_key
                        if roi_matcher.handling_strategy.value == "merge"
                        else f"{roi_key}__[{many_rois[0]}]",
                    )

        # convert to sitk image
        mask_image = sitk.GetImageFromArray(mask_array_4d, isVector=True)
        mask_image.CopyInformation(reference_image)

        assert mask_image.GetPixelIDValue() == 13
        assert mask_image.GetNumberOfComponentsPerPixel() == len(matched_rois)

        return VectorMask(
            mask_image,
            mapping,
            metadata=self.metadata,
            errors=self.roi_map_errors,
        )


if __name__ == "__main__":  # pragma: no cover
    from rich import print  # noqa

    cptac = {
        "mr": Path("data/CPTAC-UCEC/C3L-02403/MR_Series-45733428.4/"),
        "rt_seed": Path(
            "data/CPTAC-UCEC/C3L-02403/RTSTRUCT_Series-558960.4/00000001.dcm"
        ),
        "rt_contour2": Path(
            "data/CPTAC-UCEC/C3L-02403/RTSTRUCT_Series-520374.4/00000001.dcm"
        ),
        "rt_contour": Path(
            "data/CPTAC-UCEC/C3L-02403/RTSTRUCT_Series-55458746/00000001.dcm"
        ),
    }

    rt_seed = RTStructureSet.from_dicom(cptac["rt_seed"])
    print("[red]THIS SHOULD HAVE ERRORS[/red]")
    print(rt_seed)

    rt_contour = RTStructureSet.from_dicom(cptac["rt_contour"])
    rt_contour2 = RTStructureSet.from_dicom(cptac["rt_contour2"])
    print("[green]THESE SHOULD NOT HAVE ERRORS[/green]")
    print(rt_contour)
    print(rt_contour2)
