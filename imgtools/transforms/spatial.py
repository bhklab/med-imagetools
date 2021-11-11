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
             anti_alias_sigma: float = 2.,
             transform: sitk.Transform = None) -> sitk.Image:
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
        raise ValueError(f"interpolator must be one of {list(INTERPOLATORS.keys())}, got {interpolation}.")

    original_spacing = np.array(image.GetSpacing())
    original_size = np.array(image.GetSize())

    if isinstance(spacing, (float, int)):
        new_spacing = np.repeat(spacing, len(original_spacing)).astype(np.float64)
    else:
        spacing = np.asarray(spacing)
        new_spacing = np.where(spacing == 0, original_spacing, spacing)
    new_size = np.floor(original_size * original_spacing / new_spacing).astype(np.int)

    rif = sitk.ResampleImageFilter()
    rif.SetOutputOrigin(image.GetOrigin())
    rif.SetOutputSpacing(new_spacing)
    rif.SetOutputDirection(image.GetDirection())
    rif.SetSize(new_size.tolist())

    if transform is not None:
        rif.SetTransform(transform)

    downsample = new_spacing > original_spacing
    if downsample.any() and anti_alias:
        sigma = np.where(downsample, anti_alias_sigma, 1e-11)
        image = sitk.SmoothingRecursiveGaussian(image, sigma) # TODO implement better sigma computation

    rif.SetInterpolator(interpolator)
    resampled_image = rif.Execute(image)

    return resampled_image


def resize(image, new_size, interpolation="linear"):

    original_size = np.array(image.GetSize())
    original_spacing = np.array(image.GetSpacing())
    new_size = np.asarray(new_size)
    new_spacing = original_spacing * original_size / new_size

    return resample(image, new_spacing, interpolation=interpolation)

def rotate(image, rotation_centre, angles, interpolation="linear"):
    rotation_centre = image.TransformIndexToPhysicalPoint(rotation_centre)
    x_angle, y_angle, z_angle = angles

    rotation = sitk.Euler3DTransform(
        rotation_centre,
        x_angle,     # the angle of rotation around the x-axis, in radians -> coronal rotation
        y_angle,     # the angle of rotation around the y-axis, in radians -> saggittal rotation
        z_angle,     # the angle of rotation around the z-axis, in radians -> axial rotation
        (0., 0., 0.) # optional translation (shift) of the image, here we don't want any translation
    )
    return resample(image, spacing=image.GetSpacing(), interpolation=interpolation, transform=rotation)



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


def centre_on_point(image, centre):
    pass


# def resize_by_cropping_or_padding(image, size, centre=None, cval=0.):
#     original_size = np.array(image.GetSize())
#     size = np.asarray(size)
#     centre = np.asarray(centre) if centre is not None else original_size / 2 # XXX is there any benefit to not using floor div here?

#     crop_dims = np.where(size < original_size)



