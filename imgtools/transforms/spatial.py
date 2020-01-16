import SimpleITK as sitk
import numpy as np

from typing import Sequence, Union, Tuple


INTERPOLATORS = {
    "linear": sitk.sitkLinear,
    "nearest": sitk.sitkNearestNeighbor,
    "bspline": sitk.sitkBSpline,
}

def resample_image(image: sitk.Image,
                   spacing: Union[Sequence[float], float],
                   mask: Union[sitk.Image, None] = None,
                   interpolation: str = "linear",
                   anti_alias: bool = True,
                   anti_alias_sigma: float = 2.) -> Union[sitk.Image, Tuple(sitk.Image)]:
    """Resample image and (optionally) mask to a given spacing.


    Parameters
    ----------
    image
        The image to be resampled.

    spacing
        The new image spacing.

    mask, optional
        Mask with the same geometry as image to be resampled.

    interpolation, optional
        The interpolation method to use. Valid options are:
        - "linear" for bi/trilinear interpolation (default)
        - "nearest" for nearest neighbour interpolation
        - "bspline" for order-3 b-spline interpolation

    anti_alias, optional
        Whether to smooth the image with a Gaussian kernel before resampling.
        Only used when downsampling, i.e. when `spacing < image.GetSpacing()`.
        This should be used to avoid aliasing artifacts.

    anti_alias_sigma, optional
        The standard deviation of the Gaussian kernel used for anti-aliasing.


    Returns
    -------
    out : sitk.Image or tuple of sitk.Image
        The resampled image. If mask is given, also return resampled mask.

    """

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

    rif.SetInterpolator(interpolator)
    resampled_image = rif.Execute(image)
    if mask is not None:
        rif.SetInterpolator(sitk.sitkNearestNeighbor)
        resampled_mask = rif.Execute(mask)
        return resampled_image, resampled_mask

    return resampled_image
