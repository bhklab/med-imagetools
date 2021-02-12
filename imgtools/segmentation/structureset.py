import re
from warnings import warn
from typing import Dict, List, Optional, Union

import numpy as np
import SimpleITK as sitk
from pydicom import dcmread
from itertools import chain, groupby
from skimage.draw import polygon2mask

from .segmentation import Segmentation
from ..utils import physical_points_to_idxs
from ..utils import array_to_image


def _get_roi_points(rtstruct, roi_index):
    contour_data = (slc.ContourData for slc in rtstruct.ROIContourSequence[roi_index].ContourSequence)
    return np.fromiter(chain.from_iterable(contour_data), dtype=np.float64).reshape(-1, 3)


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
        labels = {}
        cur_label = 0
        for pat in names:
            if isinstance(pat, str):
                matched = False
                for name in self.roi_names:
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
            force_missing: bool = False) -> Segmentation:
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
        if not labels:
            raise ValueError(f"No ROIs matching {roi_names} found in {self.roi_names}.")

        size = reference_image.GetSize()[::-1] + (len(set(labels.values())),)

        mask = np.zeros(size, dtype=np.uint8)

        for name, label in labels.items():
            physical_points = self.roi_points.get(name, np.array([]))
            if physical_points.size == 0:
                continue # allow for missing labels, will return a blank slice

            mask_points = physical_points_to_idxs(reference_image, physical_points, continuous=True)[:, ::-1]

            slices = np.unique(mask_points[:, 0])
            for slc in slices:
                slice_points = mask_points[mask_points[:, 0] == slc, 1:]
                slice_mask = polygon2mask(size[1:-1], slice_points)
                mask[int(round(slc)), :, :, label] = slice_mask

        mask = sitk.GetImageFromArray(mask, isVector=True)
        mask.CopyInformation(reference_image)
        seg_roi_names = {"_".join(k): v for v, k in groupby(labels, key=lambda x: labels[x])}
        mask = Segmentation(mask, roi_names=seg_roi_names)

        return mask

    def __repr__(self):
        return f"<StructureSet with ROIs: {self.roi_names!r}>"
