import SimpleITK as sitk
import numpy as np

import warnings


def check_mask_geometry(reference_image, mask, tolerance=1e-5, correct_if_different=False):
    reference_geometry = (reference_image.GetOrigin(), reference_image.GetSpacing(), reference_image.GetDirection())
    mask_geometry = (mask.GetOrigin(), mask.GetSpacing(), mask.GetDirection())
    if not all((np.allclose(ref, target, atol=tolerance) for ref, target in zip(reference_geometry, mask_geometry))):
        msg = "Geometry mismatch: \
               reference origin = {reference_geometry[0]}, spacing = {reference_geometry[1]}, direction = {reference_geometry[2]}, \
               mask origin = {mask_geometry[0]}, spacing = {mask_geometry[1]}, direction = {mask_geometry[2]}."
        if correct_if_different:
            warnings.warn(msg + " Copying reference information.")
            mask.CopyInformation(reference_image)
        else:
            raise ValueError(msg)
    return reference_image, mask

