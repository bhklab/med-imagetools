from functools import wraps
import warnings

import numpy as np
import SimpleITK as sitk

from .sparsemask import SparseMask

from ..utils import array_to_image, image_to_array
from typing import Dict, List, Optional, Union, Tuple, Set


def accepts_segmentations(f):
    @wraps(f)
    def wrapper(img, *args, **kwargs):
         result = f(img, *args, **kwargs)
         if isinstance(img, Segmentation):
             result = sitk.Cast(result, sitk.sitkVectorUInt8)
             return Segmentation(result, roi_names=img.roi_names)
         else:
             return result
    return wrapper


def map_over_labels(segmentation, f, include_background=False, return_segmentation=True, **kwargs):
    if include_background:
        labels = range(segmentation.num_labels + 1)
    else:
        labels = range(1, segmentation.num_labels + 1)
    res = [f(segmentation.get_label(label=label), **kwargs) for label in labels]
    if return_segmentation and isinstance(res[0], sitk.Image):
        res = [sitk.Cast(r, sitk.sitkUInt8) for r in res]
        res = Segmentation(sitk.Compose(*res), roi_names=segmentation.roi_names)
    return res


class Segmentation(sitk.Image):
    def __init__(self, segmentation, roi_names=None, existing_roi_names=None):
        super().__init__(segmentation)
        self.num_labels = self.GetNumberOfComponentsPerPixel()
        if not roi_names:
            self.roi_names = {f"label_{i}": i for i in range(1, self.num_labels+1)}
        else:
            self.roi_names = roi_names
            if 0 in self.roi_names.values():
                self.roi_names = {k : v+1 for k, v in self.roi_names.items()}
        if len(self.roi_names) != self.num_labels:
            for i in range(1, self.num_labels+1):
                if i not in self.roi_names.values():
                    self.roi_names[f"label_{i}"] = i
        self.existing_roi_names = existing_roi_names

    def get_label(self, label=None, name=None, relabel=False):
        if label is None and name is None:
            raise ValueError("Must pass either label or name.")

        if label is None:
            label = self.roi_names[name]

        if label == 0:
            # background is stored implicitly and needs to be computed
            label_arr = sitk.GetArrayViewFromImage(self)
            label_img = sitk.GetImageFromArray((label_arr.sum(-1) == 0).astype(np.uint8))
        else:
            label_img = sitk.VectorIndexSelectionCast(self, label - 1)
            if relabel:
                label_img *= label

        return label_img

    def to_label_image(self):
        arr, *_ = image_to_array(self)
        # TODO handle overlapping labels
        label_arr = np.where(arr.sum(-1) != 0, arr.argmax(-1) + 1, 0)
        label_img = array_to_image(label_arr, reference_image=self)
        return label_img

    # TODO also overload other operators (arithmetic, etc.)
    # with some sensible behaviour

    def __getitem__(self, idx):
        res = super().__getitem__(idx)
        if isinstance(res, sitk.Image):
            res = Segmentation(res, self.roi_names)
        return res

    def __repr__(self):
        return f"<Segmentation with ROIs: {self.roi_names!r}>"
         
    def generate_sparse_mask(self, verbose=False) -> SparseMask:
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
        # print("asdlkfjalkfsjg", self.roi_names)
        mask_arr = np.transpose(sitk.GetArrayFromImage(self))
        for name in self.roi_names.keys():
            self.roi_names[name] = self.existing_roi_names[name]
        # print(self.roi_names)
        
        sparsemask_arr = np.zeros(mask_arr.shape[1:])
        
        if verbose:
            voxels_with_overlap = set()

        if len(mask_arr.shape) == 4:
            for i in range(mask_arr.shape[0]):
                slice = mask_arr[i, :, :, :]
                slice *= list(self.roi_names.values())[i] # everything is 0 or 1, so this is fine to convert filled voxels to label indices
                if verbose:
                    res = self._max_adder(sparsemask_arr, slice)
                    sparsemask_arr = res[0]
                    for e in res[1]:
                        voxels_with_overlap.add(e)
                else:
                    sparsemask_arr = np.fmax(sparsemask_arr, slice) # elementwise maximum
        else:
            sparsemask_arr = mask_arr
        
        sparsemask = SparseMask(sparsemask_arr, self.roi_names)

        if verbose:
            if len(voxels_with_overlap) != 0:
                warnings.warn(f"{len(voxels_with_overlap)} voxels have overlapping contours.")
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