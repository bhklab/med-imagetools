import SimpleITK as sitk
import numpy as np

from typing import Sequence, Union, Tuple, Optional


INTERPOLATORS = {
    "linear": sitk.sitkLinear,
    "nearest": sitk.sitkNearestNeighbor,
    "bspline": sitk.sitkBSpline,
}

def resample(image: sitk.Image,
             spacing: Union[Sequence[float], float],
             interpolation: str = "linear",
             anti_alias: bool = True,
             anti_alias_sigma: float = 2.) -> sitk.Image:
    """Resample image to a given spacing.


    Parameters
    ----------
    image
        The image to be resampled.

    spacing
        The new image spacing. If float, assumes the same spacing in all directions.
        Alternatively, a sequence of floats can be passed to specify spacing along
        x, y and z dimensions. Passing 0 at any position will keep the original
        spacing along that dimension (useful for in-plane resampling).

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
        raise ValueError(f"interpolator must be one of {list(INTERPOLATORS.keys())}, got {interpolator}.")

    original_spacing = np.array(image.GetSpacing())
    original_size = np.array(image.GetSize())

    if isinstance(spacing, (float, int)):
        new_spacing = np.repeat(spacing, len(original_spacing)).astype(np.float64)
    else:
        new_spacing = np.where(new_spacing == 0, original_spacing, new_spacing)
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

    return resampled_image


def crop(image, crop_centre, size):
    """
    
    Parameters
    ----------
    image : 

    crop_centre : 

    size : 


    Returns
    -------
    out : 

    """
    crop_centre = np.asarray(crop_centre, dtype=np.float64)
    image_shape = np.array((image.GetSize()[::-1]), dtype=np.float64)

    if isinstance(size, int):
        size_lower = size_upper = np.array([size for _ in image.GetSize()])
    elif isinstance(size, (tuple, list, np.ndarray)):
        if isinstance(size[0], int):
            size_lower = size_upper = np.asarray(size)
        elif isinstance(size[0], (tuple, list, np.ndarray)):
            size_lower = np.array([s[0] for s in size])
            size_upper = np.array([s[1] for s in size])

    if (crop_centre < 0).any() or (crop_centre > image_shape).any():
        raise ValueError(f"Crop centre outside image boundaries. Image shape = {image_shape}, crop centre = {crop_centre}")

    min_x, min_y, min_z = np.clip(np.floor((image_shape - size_lower) / 2).astype(np.int64), 0, image_shape)
    max_x, max_y, max_z = np.clip(np.floor((image_shape + size_upper) / 2).astype(np.int64), 0, image_shape)

    return image[min_x:max_x, min_y:max_y, min_z:max_z]


def constant_pad(image, size, cval=0.):
    if isinstance(size, int):
        size_lower = size_upper = [size for _ in image.GetSize()]
    elif isinstance(size, (tuple, list, np.ndarray)):
        if isinstance(size[0], int):
            size_lower = size_upper = size
        elif isinstance(size[0], (tuple, list, np.ndarray)):
            size_lower = [s[0] for s in size]
            size_upper = [s[1] for s in size]
    else:
        raise ValueError(f"Size must be either int, sequence of int or sequence of sequences of ints, got {size}.")
    return sitk.ConstantPad(image, size_lower, size_upper, cval)


