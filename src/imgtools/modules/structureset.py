"""
Module for handling and converting DICOM RTSTRUCT contour data to segmentations.

This module provides classes and methods for processing DICOM RTSTRUCT files,
which store contour data for regions of interest (ROIs). The main class,
`StructureSet`, facilitates the extraction, manipulation, and conversion of
contour data into 3D masks or segmentations compatible with other imaging
pipelines.

Classes
-------
StructureSet
    Represents a DICOM RTSTRUCT file, allowing operations such as loading
        ROI contours, converting physical points to masks, and exporting to
        segmentation objects.

Functions
---------
_get_roi_points(rtstruct, roi_index)
    Extracts and reshapes contour points for a specific ROI in an RTSTRUCT
        file.

Notes
-----
The `StructureSet` class provides utility methods for handling complex ROI
labeling schemes, such as those based on regular expressions, and supports
multiple output formats for segmentation masks. It also integrates robust
error handling and logging to handle malformed or incomplete DICOM files.
"""

import re
from itertools import groupby
from typing import Dict, List, Optional, TypeVar, Union

import numpy as np
import SimpleITK as sitk
from pydicom import dcmread
from pydicom.dataset import FileDataset
from skimage.draw import polygon2mask

from imgtools.logging import logger
from imgtools.modules.segmentation import Segmentation
from imgtools.utils import physical_points_to_idxs

T = TypeVar("T")


class StructureSet:
    def __init__(
        self,
        roi_points: Dict[str, List[np.ndarray]],
        metadata: Optional[Dict[str, T]] = None,
    ) -> None:
        """Initialize the StructureSet class containing contour points.

        Parameters
        ----------
        roi_points : Dict[str, List[np.ndarray]]
            A dictionary mapping ROI (Region of Interest) names to a list of 2D arrays.
            Each array contains the 3D physical coordinates of the contour points for a slice.
        metadata : Optional[Dict[str, T]], optional
            A dictionary containing additional metadata from the DICOM RTSTRUCT file.
            Default is an empty dictionary.

        Examples
        --------
        >>> roi_points = {'GTV': [np.array([[0, 0, 0], [1, 1, 1]])]}
        >>> metadata = {'PatientName': 'John Doe'}
        >>> structure_set = StructureSet(roi_points, metadata)
        """
        self.roi_points: Dict[str, List[np.ndarray]] = roi_points
        self.metadata: Dict[str, T] = metadata if metadata is not None else {}

    @classmethod
    def from_dicom_rtstruct(
        cls, rtstruct_path: str, suppress_warnings: bool = False
    ) -> "StructureSet":
        """Create a StructureSet instance from a DICOM RTSTRUCT file.

        Parameters
        ----------
        rtstruct_path : str
            Path to the DICOM RTSTRUCT file.
        suppress_warnings : bool, optional
            If True, suppresses warnings for missing or invalid ROI data. Default is False.

        Returns
        -------
        StructureSet
            An instance of the StructureSet class containing the ROI data and metadata.

        Raises
        ------
        FileNotFoundError
            If the specified RTSTRUCT file does not exist.
        ValueError
            If the RTSTRUCT file is invalid or cannot be read.

        Examples
        --------
        >>> structure_set = StructureSet.from_dicom_rtstruct(
        ...     'path/to/rtstruct.dcm'
        ... )
        """
        # Load the RTSTRUCT file
        rtstruct: FileDataset = dcmread(rtstruct_path, force=True)

        # Extract ROI names and points
        roi_names: List[str] = [roi.ROIName for roi in rtstruct.StructureSetROISequence]
        roi_points: Dict[str, List[np.ndarray]] = {}

        for i, name in enumerate(roi_names):
            try:
                roi_points[name] = cls._get_roi_points(rtstruct, i)
            except AttributeError as ae:
                if not suppress_warnings:
                    logger.warning(
                        f"Could not get points for ROI `{name}`.",
                        rtstruct_path=rtstruct_path,
                        error=ae,
                    )

        # Initialize metadata (can be extended later to extract more useful fields)
        metadata: Dict[str, Union[str, int, float]] = {}

        # Return the StructureSet instance
        return cls(roi_points, metadata)

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
        AttributeError
                If the ROIContourSequence, ContourSequence, or ContourData is missing or malformed.

        Examples
        --------
        >>> rtstruct = dcmread('path/to/rtstruct.dcm', force=True)
        >>> points = StructureSet._get_roi_points(rtstruct, 0)
        """
        # Check for ROIContourSequence
        if not hasattr(rtstruct, "ROIContourSequence"):
            raise AttributeError(
                "The DICOM RTSTRUCT file is missing 'ROIContourSequence'."
            )

        # Check if ROI index exists in the sequence
        if roi_index >= len(rtstruct.ROIContourSequence) or roi_index < 0:
            msg = (
                f"ROI index {roi_index} is out of bounds for the 'ROIContourSequence'."
            )
            raise AttributeError(msg)

        roi_contour = rtstruct.ROIContourSequence[roi_index]

        # Check for ContourSequence in the specified ROI
        if not hasattr(roi_contour, "ContourSequence"):
            msg = f"ROI at index {roi_index} is missing 'ContourSequence'."
            raise AttributeError(msg)

        contour_sequence = roi_contour.ContourSequence

        # Check for ContourData in each contour
        contour_points = []
        for i, slc in enumerate(contour_sequence):
            if not hasattr(slc, "ContourData"):
                msg = (
                    f"Contour {i} in ROI at index {roi_index} is missing 'ContourData'."
                )
                raise AttributeError(msg)
            contour_points.append(np.array(slc.ContourData).reshape(-1, 3))

        return contour_points

    @property
    def roi_names(self) -> List[str]:
        """List of all ROI (Region of Interest) names."""
        return list(self.roi_points.keys())

    def _assign_labels(  # noqa
        self,
        names: List[Union[str, List[str]]],
        roi_select_first: bool = False,
        roi_separate: bool = False,
    ) -> Dict[str, int]:
        """
        Assigns integer labels to ROIs (Regions of Interest) based on their names or regex patterns.

        This method supports flexible and configurable labeling of ROIs using exact matches or regular
        expressions. It also allows for advanced configurations such as selecting only the first match
        or treating each match as a separate mask.

        Parameters
        ----------
        names : List[Union[str, List[str]]]
                A list of ROI names or regex patterns. Can be:
                        - A list of strings representing exact matches or regex patterns.
                        - A nested list of regex patterns, where all matching ROIs within the same sublist
                        are assigned the same label.
        roi_select_first : bool, optional
                If True, selects only the first matching ROI for each regex pattern or name.
                Default is False.
        roi_separate : bool, optional
                If True, assigns separate labels to each matching ROI within a regex pattern, appending
                a numerical suffix to the ROI name (e.g., "CTV_0", "CTV_1"). Default is False.

        Returns
        -------
        Dict[str, int]
                A dictionary mapping ROI names to their assigned integer labels.

        Raises
        ------
        ValueError
                If `names` is empty or does not match any ROIs.

        Examples
        --------
        Lets say we have the following ROI names:
        >>> self.roi_names = ['GTV', 'PTV', 'CTV_0', 'CTV_1']

        Case 1: Default behavior
        All matching ROIs for each pattern are assigned the same label(number).
        note how the CTV ROIs are assigned the same label: 1
        >>> self._assign_labels(['GTV', 'CTV.*'])
        {'GTV': 0, 'CTV_0': 1, 'CTV_1': 1}

        Case 2: Select only the first match for each pattern
        Subsequent matches are ignored.
        >>> self._assign_labels(['GTV', 'CTV.*'], roi_select_first=True)
        {'GTV': 0, 'CTV_0': 1}

        Case 3: Separate labels for each match
        Even if a pattern matches multiple ROIs, each ROI gets a separate label.
        note how now the CTV ROIs are assigned different labels: 1 and 2
        >>> self._assign_labels(['GTV', 'CTV.*'], roi_separate=True)
        {'GTV': 0, 'CTV_0': 1, 'CTV_1': 2}

        # Case 4: Grouped patterns
        >>> self._assign_labels([['GTV', 'PTV'], 'CTV.*'])
        {'GTV': 0, 'PTV': 0, 'CTV_0': 1, 'CTV_1': 1}
        """
        if not names:
            raise ValueError("The 'names' list cannot be empty.")
        if roi_select_first and roi_separate:
            raise ValueError(
                "The options 'roi_select_first' and 'roi_separate' cannot both be True. "
                "'roi_select_first' stops after the first match,"
                " while 'roi_separate' processes all matches individually."
            )

        labels: Dict[str, int] = {}
        cur_label = 0

        # Case 1: If `names` is exactly `self.roi_names`, assign sequential labels directly.
        if names == self.roi_names:
            return {name: i for i, name in enumerate(self.roi_names)}

        # Case 2: Iterate over `names` (could contain regex patterns or sublists)
        for pattern in names:
            # TODO: refactor this to use a generator function for better readability
            # and to avoid code duplication

            # Single pattern: string or regex
            if isinstance(pattern, str):
                matched = False
                for _, roi_name in enumerate(self.roi_names):
                    if re.fullmatch(pattern, roi_name, flags=re.IGNORECASE):
                        matched = True
                        # Group all matches under the same label
                        labels[roi_name] = cur_label
                        if roi_select_first:
                            break
                # Increment label counter only if at least one match occurred
                if matched:
                    cur_label += 1

            # Nested patterns: list of strings or regexes
            elif isinstance(pattern, list):
                matched = False
                for subpattern in pattern:
                    if roi_select_first and matched:
                        break
                    for i, roi_name in enumerate(self.roi_names):
                        if re.fullmatch(subpattern, roi_name, flags=re.IGNORECASE):
                            matched = True
                            if roi_separate:
                                labels[f"{roi_name}_{i}"] = cur_label
                            else:
                                labels[roi_name] = cur_label
                cur_label += 1

            else:
                msg = f"Invalid pattern type: {type(pattern)}, expected str or list."
                raise ValueError(msg)

        # Validate output
        if not labels:
            msg = f"No matching ROIs found for the provided patterns: {names}"
            raise ValueError(msg)

        return labels

    def get_mask(self, reference_image, mask, label, idx, continuous) -> None:  # noqa
        size = reference_image.GetSize()[::-1]
        physical_points = self.roi_points.get(label, np.array([]))
        mask_points = physical_points_to_idxs(
            reference_image, physical_points, continuous=continuous
        )
        for contour in mask_points:
            try:
                z, slice_points = np.unique(contour[:, 0]), contour[:, 1:]
                if (
                    len(z) == 1
                ):  # assert len(z) == 1, f"This contour ({name}) spreads across more than 1 slice."
                    slice_mask = polygon2mask(size[1:], slice_points)
                    mask[z[0], :, :, idx] += slice_mask
            except Exception as e:  # rounding errors for points on the boundary
                if z == mask.shape[0]:
                    z -= 1
                elif z == -1:  # ?
                    z += 1
                elif z > mask.shape[0] or z < -1:
                    msg = f"{z} index is out of bounds for image sized {mask.shape}."
                    raise IndexError(msg) from e

                # if the contour spans only 1 z-slice
                if len(z) == 1:
                    z_idx = int(np.floor(z[0]))
                    slice_mask = polygon2mask(size[1:], slice_points)
                    mask[z_idx, :, :, idx] += slice_mask
                else:
                    raise ValueError(
                        "This contour is corrupted and spans across 2 or more slices."
                    ) from e

    def to_segmentation(  # noqa
        self,
        reference_image: sitk.Image,
        roi_names: Dict[str, str] = None,
        continuous: bool = True,
        existing_roi_indices: Dict[str, int] = None,
        ignore_missing_regex: bool = False,
        roi_select_first: bool = False,
        roi_separate: bool = False,
    ) -> Segmentation:
        """Convert the structure set to a Segmentation object.

        Parameters
        ----------
        reference_image
                Image used as reference geometry.
        roi_names
                List of ROI names to export. Both full names and
                case-insensitive regular expressions are allowed.
                All labels within one sublist will be assigned
                the same label.

        Returns
        -------
        Segmentation
                The segmentation object.

        Notes
        -----
        If `roi_names` contains lists of strings, each matching
        name within a sublist will be assigned the same label. This means
        that `roi_names=['pat']` and `roi_names=[['pat']]` can lead
        to different label assignments, depending on how many ROI names
        match the pattern. E.g. if `self.roi_names = ['fooa', 'foob']`,
        passing `roi_names=['foo(a|b)']` will result in a segmentation with
        two labels, but passing `roi_names=[['foo(a|b)']]` will result in
        one label for both `'fooa'` and `'foob'`.

        In general, the exact ordering of the returned labels cannot be
        guaranteed (unless all patterns in `roi_names` can only match
        a single name or are lists of strings).
        """
        labels = {}
        if roi_names is None or roi_names == {}:
            roi_names = self.roi_names  # all the contour names
            labels = self._assign_labels(
                roi_names, roi_select_first, roi_separate
            )  # only the ones that match the regex
        elif isinstance(roi_names, dict):
            for name, pattern in roi_names.items():
                if isinstance(pattern, str):
                    matching_names = list(
                        self._assign_labels([pattern], roi_select_first).keys()
                    )
                    if matching_names:
                        labels[name] = (
                            matching_names  # {"GTV": ["GTV1", "GTV2"]} is the result of _assign_labels()
                        )
                elif isinstance(
                    pattern, list
                ):  # for inputs that have multiple patterns for the input, e.g. {"GTV": ["GTV.*", "HTVI.*"]}
                    labels[name] = []
                    for pattern_one in pattern:
                        matching_names = list(
                            self._assign_labels([pattern_one], roi_select_first).keys()
                        )
                        if matching_names:
                            labels[name].extend(
                                matching_names
                            )  # {"GTV": ["GTV1", "GTV2"]}
        if isinstance(roi_names, str):
            roi_names = [roi_names]
        if isinstance(roi_names, list):  # won't this always trigger after the previous?
            labels = self._assign_labels(roi_names, roi_select_first)
        logger.debug(f"Found {len(labels)} labels", labels=labels)
        all_empty = True
        for v in labels.values():
            if v != []:
                all_empty = False
        if all_empty:
            if not ignore_missing_regex:
                msg = f"No ROIs matching {roi_names} found in {self.roi_names}."
                raise ValueError(msg)
            else:
                return None
        labels = {k: v for (k, v) in labels.items() if v != []}
        size = reference_image.GetSize()[::-1] + (len(labels),)
        mask = np.zeros(size, dtype=np.uint8)

        seg_roi_indices = {}
        if roi_names != {} and isinstance(roi_names, dict):
            for i, (name, label_list) in enumerate(labels.items()):
                for label in label_list:
                    self.get_mask(reference_image, mask, label, i, continuous)
                seg_roi_indices[name] = i

        else:
            for name, label in labels.items():
                self.get_mask(reference_image, mask, name, label, continuous)
            seg_roi_indices = {
                "_".join(k): v for v, k in groupby(labels, key=lambda x: labels[x])
            }

        mask[mask > 1] = 1
        mask = sitk.GetImageFromArray(mask, isVector=True)
        mask.CopyInformation(reference_image)
        mask = Segmentation(
            mask,
            roi_indices=seg_roi_indices,
            existing_roi_indices=existing_roi_indices,
            raw_roi_names=labels,
        )  # in the segmentation, pass all the existing roi names and then process is in the segmentation class

        return mask

    def __repr__(self) -> str:
        # return f"<StructureSet with ROIs: {self.roi_names!r}>"
        sorted_rois = sorted(self.roi_names)
        return f"<StructureSet with ROIs: {sorted_rois!r}>"
