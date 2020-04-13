import SimpleITK as sitk
from functools import wraps

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
            self.roi_names = [str(i) for i in range(self.num_labels)]
        else:
            self.roi_names = roi_names

            def get_label(self, label=None, name=None, relabel=False):
        if label is None and name is None:
            raise ValueError("Must pass either label or name.")

        if label is None:
            label = self.roi_names.index(name) + 1

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
        arr = image_to_array(self)
        # TODO handle overlapping labels
        label_arr = arr.argmax(-1)
        label_img = array_to_image(label_arr, reference_image=self)
        return label_img
