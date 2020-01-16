import SimpleITK as sitk
import numpy as np


INTERPOLATORS = {
    "linear": sitk.sitkLinear,
    "nearest": sitk.sitkNearestNeighbor,
    "bspline": sitk.sitkBSpline,
}


def resample_image(image, spacing, mask=None, interpolation="linear", anti_alias=True, anti_alias_sigma=2.):
    try:
        interpolator = INTERPOLATORS[interpolation]
    except KeyError:
        raise ValueError(f"interpolator must be one of {list(INTERPOLATORS.keys()}, got {interpolator}.")

    original_spacing = np.array(image.GetSpacing())
    original_size = np.array(image.GetSize())

    new_spacing = np.array([self.spacing, self.spacing, image.GetSpacing()[2]])
    new_size = np.floor(original_size * original_spacing / new_spacing).astype(np.int)

    rif = sitk.ResampleImageFilter()
    rif.SetOutputOrigin(image.GetOrigin())
    rif.SetOutputSpacing(new_spacing)
    rif.SetOutputDirection(image.GetDirection())
    rif.SetSize(new_size.tolist())

    downsample = new_spacing > original_spacing
    if downsample.any() and anti_alias:
        sigma = np.where(downsample, anti_alias_sigma, 1e-11)
        image = sitk.SmoothingRecursiveGaussian(image, sigma) # TODO implement better sigma computation

    rif.SetInterpolator(sitk.sitkLinear)
    resampled_image = rif.Execute(image)
    if mask is not None:
        rif.SetInterpolator(sitk.sitkNearestNeighbor)
        resampled_mask = rif.Execute(mask)
        return resampled_image, resampled_mask

    return resampled_image
