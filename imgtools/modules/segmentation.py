from functools import wraps

import numpy as np
import SimpleITK as sitk

from ..utils import array_to_image, image_to_array


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
    def __init__(self, segmentation, roi_names=None):
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
