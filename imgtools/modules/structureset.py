import re
from warnings import warn
from typing import Dict, List, Optional, Union, Tuple, Set

import numpy as np
import SimpleITK as sitk
from pydicom import dcmread
from itertools import groupby
from skimage.draw import polygon2mask

from .segmentation import Segmentation
from .sparsemask import SparseMask
from ..utils import physical_points_to_idxs


def _get_roi_points(rtstruct, roi_index):
    return [np.array(slc.ContourData).reshape(-1, 3) for slc in rtstruct.ROIContourSequence[roi_index].ContourSequence]


class StructureSet:
    def __init__(self, roi_points: Dict[str, np.ndarray]):
        self.roi_points = roi_points

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
        return cls(roi_points)

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

    def to_segmentation(self, reference_image: sitk.Image,
                        roi_names: Optional[List[Union[str, List[str]]]] = None,
                        force_missing: bool = False,
                        continuous: bool = True) -> Segmentation:
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
        if not roi_names:
            roi_names = self.roi_names
        if isinstance(roi_names, str):
            roi_names = [roi_names]
       
        labels = self._assign_labels(roi_names, force_missing)
        print("labels:", labels)
        if not labels:
            raise ValueError(f"No ROIs matching {roi_names} found in {self.roi_names}.")

        size = reference_image.GetSize()[::-1] + (max(labels.values()) + 1,)

        mask = np.zeros(size, dtype=np.uint8)

        for name, label in labels.items():
            physical_points = self.roi_points.get(name, np.array([]))
            if len(physical_points) == 0:
                continue # allow for missing labels, will return a blank slice

            mask_points = physical_points_to_idxs(reference_image, physical_points, continuous=continuous)

            for contour in mask_points:
                z, slice_points = np.unique(contour[:, 0]), contour[:, 1:]
                # rounding errors for points on the boundary
                if z == mask.shape[0]:
                    z -= 1
                elif z == -1:
                    z += 1
                elif z > mask.shape[0] or z < -1:
                    raise IndexError(f"{z} index is out of bounds for image sized {mask.shape}.")
                
                # if the contour spans only 1 z-slice 
                if len(z) == 1:
                    z = int(np.floor(z[0]))
                    slice_mask = polygon2mask(size[1:-1], slice_points)
                    mask[z, :, :, label] += slice_mask
                else:
                    raise ValueError("This contour is corrupted and spans across 2 or more slices.")

                # This is the old version of z index parsing. Kept for backup
                # if len(z) == 1:
                #     # assert len(z) == 1, f"This contour ({name}) spreads across more than 1 slice."
                #     z = z[0]
                #     slice_mask = polygon2mask(size[1:-1], slice_points)
                #     mask[z, :, :, label] += slice_mask

        
        mask[mask > 1] = 1
        mask = sitk.GetImageFromArray(mask, isVector=True)
        mask.CopyInformation(reference_image)
        seg_roi_names = {"_".join(k): v for v, k in groupby(labels, key=lambda x: labels[x])}
        mask = Segmentation(mask, roi_names=seg_roi_names)

        return mask
        
    def generate_sparse_mask(self, mask: Segmentation) -> SparseMask:
        """
        Generate a sparse mask from the contours, taking the argmax of all overlaps

        Parameters
        ----------
        mask
            Segmentation object to build sparse mask from

        Returns
        -------
        SparseMask
            The sparse mask object.
        """
        mask_arr = np.transpose(sitk.GetArrayFromImage(mask))
        roi_names = {k: v+1 for k, v in mask.roi_names.items()}
        
        sparsemask_arr = np.zeros(mask_arr.shape[1:])

        # voxels_with_overlap = {}
        for i in len(mask_arr.shape[0]):
            slice = mask_arr[i, :, :, :]
            slice *= list(roi_names.values())[i] # everything is 0 or 1, so this is fine to convert filled voxels to label indices
            # res = self._max_adder(sparsemask_arr, slice)
            # sparsemask_arr = res[0]
            # for e in res[1]:
            #     voxels_with_overlap.add(e)
            sparsemask_arr = np.fmax(sparsemask_arr, slice) # elementwise maximum
        
        sparsemask = SparseMask(sparsemask_arr, roi_names)
        # if len(voxels_with_overlap) != 0:
        #     raise Warning(f"{len(voxels_with_overlap)} voxels have overlapping contours.")
        return sparsemask

    def _max_adder(self, arr_1: np.ndarray, arr_2: np.ndarray) -> Tuple[np.ndarray, Set[Tuple[int, int, int]]]:
        """
        Takes the maximum of two 3D arrays elementwise and returns the resulting array and a list of voxels that have overlapping contours in a set

        Parameters
        ----------
        arr_1
            First array to take maximum of
        arr_2
            Second array to take maximum of
        
        Returns
        -------
        Tuple[np.ndarray, Set[Tuple[int, int, int]]]
            The resulting array and a list of voxels that have overlapping contours in a set
        """
        res = np.zeros(arr_1.shape)
        overlaps = {} #set of tuples of the coords that have overlap
        for i in range(arr_1.shape[0]):
            for j in range(arr_1.shape[1]):
                for k in range(arr_1.shape[2]):
                    if arr_1[i, j, k] != 0 and arr_2[i, j, k] != 0:
                        overlaps.add((i, j, k))
                    res[i, j, k] = max(arr_1[i, j, k], arr_2[i, j, k])
        return res, overlaps

    def __repr__(self):
        return f"<StructureSet with ROIs: {self.roi_names!r}>"
