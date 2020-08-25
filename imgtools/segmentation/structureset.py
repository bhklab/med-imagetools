import re
import numpy as np
import SimpleITK as sitk
from pydicom import dcmread
from collections import OrderedDict
from itertools import chain
from skimage.draw import polygon2mask

from .segmentation import Segmentation
from ..utils import physical_points_to_idxs
from ..utils import array_to_image


def _get_roi_points(rtstruct, roi_index):
    contour_data = (slc.ContourData for slc in rtstruct.ROIContourSequence[roi_index].ContourSequence)
    return np.fromiter(chain.from_iterable(contour_data), dtype=np.float64).reshape(-1, 3)


class StructureSet:
    def __init__(self, roi_points):
        self.roi_points = roi_points

    @classmethod
    def from_dicom_rtstruct(cls, rtstruct_path):
        rtstruct = dcmread(rtstruct_path, force=True)
        roi_names = [roi.ROIName for roi in rtstruct.StructureSetROISequence]

        roi_points = {}
        for i, name in enumerate(roi_names):
            try:
                roi_points[name] = _get_roi_points(rtstruct, i)
            except AttributeError:
                # XXX maybe log a warning if a ROI has no points?
                pass
        return cls(roi_points)

    @property
    def roi_names(self):
        return list(self.roi_points.keys())

    def to_segmentation(self, reference_image, roi_names=None):
        if not roi_names:
            roi_names = self.roi_names
        if isinstance(roi_names, str):
            roi_names = [roi_names]

        names_to_use = list(chain.from_iterable((name for name in self.roi_names if re.fullmatch(pat, name, flags=re.IGNORECASE)) for pat in roi_names))

        if not names_to_use:
            raise ValueError(f"No ROIs matching {roi_names} found in {self.roi_names}.")

        size = reference_image.GetSize()[::-1] + (len(names_to_use),)

        mask = np.zeros(size, dtype=np.uint8)

        for label, name in enumerate(names_to_use):
            physical_points = self.roi_points.get(name)
            if physical_points.size == 0:
                continue # allow for missing labels, will return a blank slice

            mask_points = physical_points_to_idxs(reference_image, physical_points, continuous=True)[:, ::-1]

            slices = np.unique(mask_points[:, 0])
            for slc in slices:
                slice_points = mask_points[mask_points[:, 0] == slc, 1:]
                slice_mask = polygon2mask(size[1:-1], slice_points)
                mask[int(slc), :, :, label] = slice_mask

        mask = sitk.GetImageFromArray(mask, isVector=True)
        mask.CopyInformation(reference_image)
        mask = Segmentation(mask, roi_names=names_to_use)

        return mask
