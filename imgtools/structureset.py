import re
import numpy as np
import SimpleITK as sitk
from pydicom import dcmread
from collections import OrderedDict
from itertools import chain
from skimage.draw import polygon2mask

from .utils import physical_points_to_idxs
from .utils import array_to_image


def _get_roi_points(rtstruct, roi_index):
    contour_data = (slc.ContourData for slc in rtstruct.ROIContourSequence[roi_index].ContourSequence)
    return np.fromiter(chain.from_iterable(contour_data), dtype=np.float64).reshape(-1, 3)


# def label_to_onehot(mask):
#     pass

# def onehot_to_label(mask):#, overlapping="new"):
#     pass
#     # mask_onehot = np.argmax(mask, axis=-1)
#     # return mask_onehot

class StructureSet:
    def __init__(self, roi_names, roi_points):
        self.segmentation_points = OrderedDict(zip(roi_names, roi_points))

    @classmethod
    def from_dicom_rtstruct(cls, rtstruct_path):
        rtstruct = dcmread(rtstruct_path, force=True)
        roi_names = [roi.ROIName for roi in rtstruct.StructureSetROISequence]
        roi_points = [_get_roi_points(rtstruct, i) for i, name in enumerate(roi_names)]
        return cls(roi_names, roi_points)

    @property
    def roi_names(self):
        return list(self.segmentation_points.keys())

    def to_mask(self, reference_image, roi_names=None):
        if not roi_names:
            roi_names = self.roi_names
        if isinstance(roi_names, str):
            roi_names = [roi_names]
        roi_names = [name for name in self.roi_names if any(re.match(roi, name) for roi in self.roi_names)]
        roi_points = [self.segmentation_points.get(name) for name in roi_names]

        size = reference_image.GetSize()[::-1] + (len(roi_names) + 1,)

        mask = np.zeros(size, dtype=np.uint8)

        # TODO (Michal) add support for overlapping labels
        # using SimpleITK vector-valued images
        for label, physical_points in enumerate(roi_points):
            if physical_points is None:
                continue # allow for missing labels, will return a blank slice

            mask_points = physical_points_to_idxs(reference_image, physical_points, continuous=True)[:, ::-1]

            slices = np.unique(mask_points[:, 0])
            for slc in slices:
                slice_points = mask_points[mask_points[:, 0] == slc, 1:]
                slice_mask = polygon2mask(size[1:-1], slice_points)
                mask[int(slc), :, :, label + 1] = slice_mask

        mask = array_to_image(mask.argmax(-1), reference_image=reference_image)

        return mask
