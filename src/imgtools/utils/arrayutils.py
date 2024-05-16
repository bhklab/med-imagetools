import numpy as np
import SimpleITK as sitk


def array_to_image(array,
                   origin=(0., 0., 0.),
                   direction=(1., 0., 0., 0., 1., 0., 0., 0., 1.),
                   spacing=(1., 1., 1.),
                   reference_image=None):
    image = sitk.GetImageFromArray(array)
    if reference_image is not None:
        image.CopyInformation(reference_image)
    else:
        image.SetOrigin(origin)
        image.SetDirection(direction)
        image.SetSpacing(spacing)

    return image


def find_slices_with_labels(array, labels=None):
    if not labels:
        return np.where(array.sum(axis=(1, 2)) > 0)[0]
    else:
        if isinstance(labels, int):
            labels = [labels]
        return np.where(np.isin(array, labels).sum(axis=(1, 2)) > 0)[0]
