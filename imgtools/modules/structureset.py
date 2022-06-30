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

    def _assign_labels(self, names, force_missing=False):
        """
        args
        ----
        force_missing
            What does force_missing do?
        """
        labels = {}
        cur_label = 0
        if names == self.roi_names:
            for i, name in enumerate(self.roi_names):
                labels[name] = i
        else:
            for _, pat in enumerate(names):
                if sorted(names) == sorted(list(labels.keys())): #checks if all ROIs have already been processed.
                    break
                if isinstance(pat, str):
                    matched = False
                    for i, name in enumerate(self.roi_names):
                        if re.fullmatch(pat, name, flags=re.IGNORECASE):
                            labels[name] = cur_label
                            cur_label += 1
                            matched = True
                    if force_missing and not matched:
                        labels[pat] = cur_label
                        cur_label += 1
                else:
                    matched = False
                    for subpat in pat:
                        for name in self.roi_names:
                            if re.fullmatch(subpat, name, flags=re.IGNORECASE):
                                labels[name] = cur_label
                                matched = True
                    if force_missing and not matched:
                        key = '_'.join(pat)
                        labels[key] = cur_label
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
                        force_missing: bool = False,
                        continuous: bool = True,
                        existing_roi_names: Dict[str, int] = None,
                        ignore_missing_regex: bool = False) -> Segmentation:
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
        force_missing
            If True, the number of labels in the output will
            be equal to `len(roi_names)`, with blank slices for
            any missing labels. Otherwise, missing ROI names
            will be excluded.

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
            labels = self._assign_labels(roi_names, force_missing) #only the ones that match the regex
        elif isinstance(roi_names, dict):
            for name, pattern in roi_names.items():
                if isinstance(pattern, str):
                    matching_names = list(self._assign_labels([pattern], force_missing).keys())
                    if matching_names:
                        labels[name] = matching_names #{"GTV": ["GTV1", "GTV2"]} is the result of _assign_labels()
                elif isinstance(pattern, list): # for inputs that have multiple patterns for the input, e.g. {"GTV": ["GTV.*", "HTVI.*"]}
                    labels[name] = []
                    for pat in pattern:
                        matching_names = list(self._assign_labels([pat], force_missing).keys())
                        if matching_names:
                            labels[name].extend(matching_names) #{"GTV": ["GTV1", "GTV2"]}
        if isinstance(roi_names, str):
            roi_names = [roi_names]
        if isinstance(roi_names, list):
            labels = self._assign_labels(roi_names, force_missing)
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

        # size = reference_image.GetSize()[::-1] + (max(labels.values()) + 1,)
        size = reference_image.GetSize()[::-1] + (len(labels),)
        # print(size)
        # print(reference_image.GetSize()[::-1])
        # print((max(labels.values()) + 1,))

        mask = np.zeros(size, dtype=np.uint8)

        # print(self.roi_points)

        

        seg_roi_names = {}
        if roi_names != {} and isinstance(roi_names, dict):
            for i, (name, label_list) in enumerate(labels.items()):
                for label in label_list:
                    self.get_mask(reference_image, mask, label, i, continuous)
                    # physical_points = self.roi_points.get(label, np.array([]))
                    # mask_points = physical_points_to_idxs(reference_image, physical_points, continuous=continuous)
                    # for contour in mask_points:
                    #     z, slice_points = np.unique(contour[:, 0]), contour[:, 1:]
                    #     if len(z) == 1:
                    #         #f assert len(z) == 1, f"This contour ({name}) spreads across more than 1 slice."
                    #         z = z[0]
                    #         slice_mask = polygon2mask(size[1:-1], slice_points)
                    #         mask[z, :, :, i] += slice_mask
                seg_roi_names[name] = i
        else:
            for name, label in labels.items():
                self.get_mask(reference_image, mask, name, label, continuous)
                # physical_points = self.roi_points.get(name, np.array([]))
                # # print(physical_points) #np.ndarray, 3d array with the physical locations (float coordinates)
                # if len(physical_points) == 0:
                #     continue # allow for missing labels, will return a blank slice

                # mask_points = physical_points_to_idxs(reference_image, physical_points, continuous=continuous)
                # # print(mask_points)
                
                # # print(mask.shape, "asldkfjalsk")
                # for contour in mask_points:
                #     z, slice_points = np.unique(contour[:, 0]), contour[:, 1:]
                #     # rounding errors for points on the boundary
                #     # if z == mask.shape[0]:
                #     #     z -= 1
                #     # elif z == -1:
                #     #     z += 1
                #     # elif z > mask.shape[0] or z < -1:
                #     #     raise IndexError(f"{z} index is out of bounds for image sized {mask.shape}.")
                    
                #     # # if the contour spans only 1 z-slice 
                #     # if len(z) == 1:
                #     #     z = int(np.floor(z[0]))
                #     #     slice_mask = polygon2mask(size[1:-1], slice_points)
                #     #     mask[z, :, :, label] += slice_mask
                #     # else:
                #     #     raise ValueError("This contour is corrupted and spans across 2 or more slices.")

                #     # This is the old version of z index parsing. Kept for backup
                #     if len(z) == 1:
                #         # assert len(z) == 1, f"This contour ({name}) spreads across more than 1 slice."
                #         z = z[0]
                #         slice_mask = polygon2mask(size[1:-1], slice_points)
                #         mask[z, :, :, label] += slice_mask
            seg_roi_names = {"_".join(k): v for v, k in groupby(labels, key=lambda x: labels[x])}

        
        mask[mask > 1] = 1
        mask = sitk.GetImageFromArray(mask, isVector=True)
        mask.CopyInformation(reference_image)
        mask = Segmentation(mask, roi_names=seg_roi_names, existing_roi_names=existing_roi_names) #in the segmentation, pass all the existing roi names and then process is in the segmentation class

        return mask

    def __repr__(self):
        return f"<StructureSet with ROIs: {self.roi_names!r}>"
