import re
from warnings import warn
from typing import Dict, List, Optional, Union, Tuple, Set, TypeVar
import copy

import numpy as np
import SimpleITK as sitk
from pydicom import dcmread
from itertools import groupby
from skimage.draw import polygon2mask

from .segmentation import Segmentation
from ..utils import physical_points_to_idxs

T = TypeVar('T')

def _get_roi_points(rtstruct, roi_index):
    return [np.array(slc.ContourData).reshape(-1, 3) for slc in rtstruct.ROIContourSequence[roi_index].ContourSequence]


class StructureSet:
    def __init__(self, roi_points: Dict[str, np.ndarray], metadata: Optional[Dict[str, T]] = None):
        """Initializes the StructureSet class containing contour points
        
        Parameters
        ----------
        roi_points
            Dictionary of {"ROI": [ndarray of shape n x 3 of contour points]}
        
        metadata
            Dictionary of DICOM metadata
        """
        self.roi_points = roi_points
        if metadata:
            self.metadata = metadata
        else:
            self.metadata = {}

    @classmethod
    def from_dicom_rtstruct(cls, rtstruct_path: str) -> 'StructureSet':
        rtstruct = dcmread(rtstruct_path, force=True)
        roi_names = [roi.ROIName for roi in rtstruct.StructureSetROISequence]
        roi_points = {}
        for i, name in enumerate(roi_names):
            try:
                roi_points[name] = _get_roi_points(rtstruct, i)
            except AttributeError:
                warn(f"Could not get points for ROI {name} (in {rtstruct_path}).")

        metadata = {}
        
        return cls(roi_points, metadata)
        # return cls(roi_points)

    @property
    def roi_names(self) -> List[str]:
        return list(self.roi_points.keys())

    def _assign_labels(self, 
                       names, 
                       roi_select_first: bool = False,
                       roi_separate: bool = False):
        """
        Parameters
        ----
        roi_select_first
            Select the first matching ROI/regex for each OAR, no duplicate matches. 

        roi_separate
            Process each matching ROI/regex as individual masks, instead of consolidating into one mask
            Each mask will be named ROI_n, where n is the nth regex/name/string.
        """
        labels = {}
        cur_label = 0
        if names == self.roi_names:
            for i, name in enumerate(self.roi_names):
                labels[name] = i
        else:
            for _, pattern in enumerate(names):
                if sorted(names) == sorted(list(labels.keys())): #checks if all ROIs have already been processed.
                    break
                if isinstance(pattern, str):
                    for i, name in enumerate(self.roi_names):
                        if re.fullmatch(pattern, name, flags=re.IGNORECASE):
                            labels[name] = cur_label
                            cur_label += 1
                else: # if multiple regex/names to match
                    matched = False
                    for subpattern in pattern:
                        if roi_select_first and matched: break # break if roi_select_first and we're matched

                        for n, name in enumerate(self.roi_names):
                            if re.fullmatch(subpattern, name, flags=re.IGNORECASE):
                                matched = True
                                if not roi_separate:
                                    labels[name] = cur_label
                                else:
                                    labels[f"{name}_{n}"] = cur_label
                                
                    cur_label += 1
        return labels

    def get_mask(self, reference_image, mask, label, idx, continuous):
        size = reference_image.GetSize()[::-1]
        physical_points = self.roi_points.get(label, np.array([]))
        mask_points = physical_points_to_idxs(reference_image, physical_points, continuous=continuous)
        for contour in mask_points:
            try:
                z, slice_points = np.unique(contour[:, 0]), contour[:, 1:]
                if len(z) == 1:
                    #f assert len(z) == 1, f"This contour ({name}) spreads across more than 1 slice."
                    z = z[0]
                    slice_mask = polygon2mask(size[1:], slice_points)
                    mask[z, :, :, idx] += slice_mask
            except: # rounding errors for points on the boundary
                if z == mask.shape[0]:
                    z -= 1
                elif z == -1:
                    z += 1
                elif z > mask.shape[0] or z < -1:
                    raise IndexError(f"{z} index is out of bounds for image sized {mask.shape}.")
                
                # if the contour spans only 1 z-slice 
                if len(z) == 1:
                    z = int(np.floor(z[0]))
                    slice_mask = polygon2mask(size[1:], slice_points)
                    mask[z, :, :, label] += slice_mask
                else:
                    raise ValueError("This contour is corrupted and spans across 2 or more slices.")

    def to_segmentation(self, reference_image: sitk.Image,
                        roi_names: Dict[str, str] = None,
                        continuous: bool = True,
                        existing_roi_names: Dict[str, int] = None,
                        ignore_missing_regex: bool = False,
                        roi_select_first: bool = False,
                        roi_separate: bool = False) -> Segmentation:
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
            roi_names = self.roi_names #all the contour names
            labels = self._assign_labels(roi_names, roi_select_first, roi_separate) #only the ones that match the regex
        elif isinstance(roi_names, dict):
            for name, pattern in roi_names.items():
                if isinstance(pattern, str):
                    matching_names = list(self._assign_labels([pattern], roi_select_first).keys())
                    if matching_names:
                        labels[name] = matching_names #{"GTV": ["GTV1", "GTV2"]} is the result of _assign_labels()
                elif isinstance(pattern, list): # for inputs that have multiple patterns for the input, e.g. {"GTV": ["GTV.*", "HTVI.*"]}
                    labels[name] = []
                    for pattern_one in pattern:
                        matching_names = list(self._assign_labels([pattern_one], roi_select_first).keys())
                        if matching_names:
                            labels[name].extend(matching_names) #{"GTV": ["GTV1", "GTV2"]}
        if isinstance(roi_names, str):
            roi_names = [roi_names]
        if isinstance(roi_names, list): # won't this always trigger after the previous?
            print("triggered")
            labels = self._assign_labels(roi_names, roi_select_first)
        print("labels:", labels)
        all_empty = True
        for v in labels.values():
            if v != []:
                all_empty = False
        if all_empty:
            if not ignore_missing_regex:
                raise ValueError(f"No ROIs matching {roi_names} found in {self.roi_names}.")
            else:
                return None
        labels = {k:v for (k,v) in labels.items() if v != [] }
        size = reference_image.GetSize()[::-1] + (len(labels),)
        mask = np.zeros(size, dtype=np.uint8)

        seg_roi_names = {}
        if roi_names != {} and isinstance(roi_names, dict):
            for i, (name, label_list) in enumerate(labels.items()):
                for label in label_list:
                    self.get_mask(reference_image, mask, label, i, continuous)
                seg_roi_names[name] = i
        else:
            for name, label in labels.items():
                self.get_mask(reference_image, mask, name, label, continuous)
            seg_roi_names = {"_".join(k): v for v, k in groupby(labels, key=lambda x: labels[x])}

        
        mask[mask > 1] = 1
        mask = sitk.GetImageFromArray(mask, isVector=True)
        mask.CopyInformation(reference_image)
        mask = Segmentation(mask, roi_names=seg_roi_names, existing_roi_names=existing_roi_names) #in the segmentation, pass all the existing roi names and then process is in the segmentation class

        return mask

    def __repr__(self):
        return f"<StructureSet with ROIs: {self.roi_names!r}>"
