from typing import List

import numpy as np
import SimpleITK as sitk

INTERPOLATORS = {
    "linear": sitk.sitkLinear,
    "nearest": sitk.sitkNearestNeighbor,
    "bspline": sitk.sitkBSpline,
}

__all__ = [
    "resample",
    "resize",
    "zoom",
    "rotate",
    "crop",
    "clip_intensity",
    "window_intensity",
]


def resample(
    image: sitk.Image,
    spacing: float | List[float] | np.ndarray,
    interpolation: str = "linear",
    anti_alias: bool = True,
    anti_alias_sigma: float | List[float] | None = None,
    transform: sitk.Transform | None = None,
    output_size: List[float] | None = None,
) -> sitk.Image:
    """Resample image to a given spacing, optionally applying a transformation.

    Parameters
    ----------
    image
        The image to be resampled.

    spacing
        The new image spacing. If float, assumes the same spacing in all
        directions. Alternatively, a sequence of floats can be passed to
        specify spacing along each dimension. Passing 0 at any position will
        keep the original spacing along that dimension (useful for in-plane
        resampling).

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

    transform, optional
        Transform to apply to input coordinates when resampling. If None,
        defaults to identity transformation.

    output_size, optional
        Size of the output image. If None, it is computed to preserve the
        whole extent of the input image.

    Returns
    -------
    sitk.Image
        The resampled image.

    Examples
    --------
    >>> resampled_image = resample_image(
    ...     example_image, [1, 1, 1]
    ... )
    >>> print(resampled_image.GetSpacing())
    [1, 1, 1]
    """

    try:
        interpolator = INTERPOLATORS[interpolation]
    except KeyError as ke:
        msg = f"interpolator must be one of {list(INTERPOLATORS.keys())}, got {interpolation}."
        raise ValueError(msg) from ke

    original_spacing = np.array(image.GetSpacing())
    original_size = np.array(image.GetSize())

    if isinstance(spacing, (float, int)):
        new_spacing = np.repeat(spacing, len(original_spacing)).astype(
            np.float64
        )
    else:
        spacing = np.asarray(spacing)
        new_spacing = np.where(spacing == 0, original_spacing, spacing)

    if output_size is None:
        new_size = np.round(
            original_size * original_spacing / new_spacing, decimals=0
        ).astype(int)
    else:
        new_size = np.asarray(output_size).astype(int)

    rif = sitk.ResampleImageFilter()
    rif.SetOutputOrigin(image.GetOrigin())
    rif.SetOutputSpacing(new_spacing)
    rif.SetOutputDirection(image.GetDirection())
    rif.SetSize(new_size.tolist())

    if transform is not None:
        rif.SetTransform(transform)

    downsample = new_spacing > original_spacing
    if downsample.any() and anti_alias:
        if not anti_alias_sigma:
            # sigma computation adapted from scikit-image
            # https://github.com/scikit-image/scikit-image/blob/master/skimage/transform/_warps.py
            anti_alias_sigma = list(
                np.maximum(1e-11, (original_spacing / new_spacing - 1) / 2)
            )
        sigma = np.where(downsample, anti_alias_sigma, 1e-11)
        image = sitk.SmoothingRecursiveGaussian(image, sigma)

    rif.SetInterpolator(interpolator)
    resampled_image = rif.Execute(image)

    return resampled_image


def resize(
    image: sitk.Image,
    size: int | List[int] | np.ndarray,
    interpolation: str = "linear",
    anti_alias: bool = True,
    anti_alias_sigma: float | None = None,
) -> sitk.Image:
    """Resize image to a given size by resampling coordinates.

    Parameters
    ----------
    image
        The image to be resize.

    size
        The new image size. If float, assumes the same size in all directions.
        Alternatively, a sequence of floats can be passed to specify size along
        each dimension. Passing 0 at any position will keep the original
        size along that dimension.

    interpolation, optional
        The interpolation method to use. Valid options are:
        - "linear" for bi/trilinear interpolation (default)
        - "nearest" for nearest neighbour interpolation
        - "bspline" for order-3 b-spline interpolation

    anti_alias, optional
        Whether to smooth the image with a Gaussian kernel before resampling.
        Only used when downsampling, i.e. when `size < image.GetSize()`.
        This should be used to avoid aliasing artifacts.

    anti_alias_sigma, optional
        The standard deviation of the Gaussian kernel used for anti-aliasing.

    Returns
    -------
    sitk.Image
        The resized image.

    Examples
    --------
    >>> print("Original Size:", example_image.GetSize())
    Original Size: [512, 512, 97]

    >>> resized_image = resize_image(
    ...     example_image, [256, 256, 0]
    ... )
    >>> print("Resized Size:", resized_image.GetSize())
    Resized Size: [256, 256, 97]
    """

    original_size = np.array(image.GetSize())
    original_spacing = np.array(image.GetSpacing())

    if isinstance(size, (float, int)):
        new_size = np.repeat(size, len(original_size)).astype(np.float64)
    else:
        size = np.asarray(size)
        new_size = np.where(size == 0, original_size, size)

    new_spacing = original_spacing * original_size / new_size

    return resample(
        image,
        new_spacing,
        anti_alias=anti_alias,
        anti_alias_sigma=anti_alias_sigma,
        interpolation=interpolation,
        output_size=list(new_size),
    )


def zoom(
    image: sitk.Image,
    scale_factor: float | List[float],
    interpolation: str = "linear",
    anti_alias: bool = True,
    anti_alias_sigma: float | None = None,
) -> sitk.Image:
    """Rescale image, preserving its spatial extent.

    The rescaled image will have the same spatial extent (size) but will be
    rescaled by `scale_factor` in each dimension. Alternatively, a separate
    scale factor for each dimension can be specified by passing a sequence
    of floats.

    Parameters
    ----------
    image
        The image to rescale.

    scale_factor
        If float, each dimension will be scaled by that factor. If tuple, each
        dimension will be scaled by the corresponding element.

    interpolation, optional
        The interpolation method to use. Valid options are:
        - "linear" for bi/trilinear interpolation (default)
        - "nearest" for nearest neighbour interpolation
        - "bspline" for order-3 b-spline interpolation

    anti_alias, optional
        Whether to smooth the image with a Gaussian kernel before resampling.
        Only used when downsampling, i.e. when `size < image.GetSize()`.
        This should be used to avoid aliasing artifacts.

    anti_alias_sigma, optional
        The standard deviation of the Gaussian kernel used for anti-aliasing.

    Returns
    -------
    sitk.Image
        The rescaled image.

    Examples
    -------
    >>> zoomed_image = zoom_image(example_image, 2.0)
    """
    dimension = image.GetDimension()

    if isinstance(scale_factor, float):
        scale_factor = (scale_factor,) * dimension

    centre_idx = np.array(image.GetSize()) / 2
    centre = image.TransformContinuousIndexToPhysicalPoint(centre_idx)

    transform = sitk.ScaleTransform(dimension, scale_factor)
    transform.SetCenter(centre)

    return resample(
        image,
        spacing=image.GetSpacing(),
        interpolation=interpolation,
        anti_alias=anti_alias,
        anti_alias_sigma=anti_alias_sigma,
        transform=transform,
        output_size=image.GetSize(),
    )


def rotate(
    image: sitk.Image,
    rotation_centre: List[float],
    angles: List[float],
    interpolation: str = "linear",
) -> sitk.Image:
    """Rotate an image around a given centre.

    Parameters
    ----------
    image
        The image to rotate.

    rotation_centre
        The centre of rotation in image coordinates.

    angles
        The angles of rotation around x, y and z axes.

    Returns
    -------
    sitk.Image
        The rotated image.

    Examples
    --------
    >>> size = example_image.GetSize()
    >>> center_voxel = [
    ...     size[i] // 2 for i in range(len(size))
    ... ]
    >>> rotated_image = rotate_image(
    ...     example_image, center_voxel, [45, 45, 45]
    ... )
    """
    if isinstance(rotation_centre, np.ndarray):
        rotation_centre = rotation_centre.tolist()

    rotation_centre = image.TransformIndexToPhysicalPoint(rotation_centre)

    rotation: sitk.Euler2DTransform | sitk.Euler3DTransform
    if image.GetDimension() == 2:
        rotation = sitk.Euler2DTransform(
            rotation_centre,
            angles,
            (0.0, 0.0),  # no translation
        )
    elif image.GetDimension() == 3:
        x_angle, y_angle, z_angle = angles

        rotation = sitk.Euler3DTransform(
            rotation_centre,
            x_angle,  # the angle of rotation around the x-axis, in radians -> coronal rotation
            y_angle,  # the angle of rotation around the y-axis, in radians -> saggittal rotation
            z_angle,  # the angle of rotation around the z-axis, in radians -> axial rotation
            (0.0, 0.0, 0.0),  # no translation
        )
    return resample(
        image,
        spacing=image.GetSpacing(),
        interpolation=interpolation,
        transform=rotation,
    )


def crop(
    image: sitk.Image,
    crop_centre: List[float] | np.ndarray,
    size: int | List[int] | np.ndarray,
) -> sitk.Image:
    """Crop an image to the desired size around a given centre.

    Note that the cropped image might be smaller than size in a particular
    direction if the cropping window exceeds image boundaries.

    Parameters
    ----------
    image
        The image to crop.

    crop_centre
        The centre of the cropping window in image coordinates.

    size
        The size of the cropping window along each dimension in pixels. If
        float, assumes the same size in all directions. Alternatively, a
        sequence of floats can be passed to specify size along x, y and z
        dimensions. Passing 0 at any position will keep the original size along
        that dimension.

    Returns
    -------
    sitk.Image
        The cropped image.

    Examples
    --------
    >>> size = example_image.GetSize()
    >>> center_voxel = [
    ...     size[i] // 2 for i in range(len(size))
    ... ]
    >>> cropped_image = crop(
    ...     example_image, center_voxel, [45, 45, 45]
    ... )
    """
    crop_centre = np.asarray(crop_centre, dtype=np.float64)
    original_size = np.asarray(image.GetSize())

    size = (
        np.array([size for _ in image.GetSize()])
        if isinstance(size, int)
        else np.asarray(size)
    )

    if (crop_centre < 0).any() or (crop_centre > original_size).any():
        msg = f"Crop centre outside image boundaries. Image size = {original_size}, crop centre = {crop_centre}"
        raise ValueError(msg)

    min_coords = np.clip(
        np.floor(crop_centre - size / 2).astype(np.int64), 0, original_size
    )
    min_coords = np.where(size == 0, 0, min_coords)

    max_coords = np.clip(
        np.floor(crop_centre + size / 2).astype(np.int64), 0, original_size
    )
    max_coords = np.where(size == 0, original_size, max_coords)

    min_x, min_y, min_z = min_coords
    max_x, max_y, max_z = max_coords

    return image[min_x:max_x, min_y:max_y, min_z:max_z]


def clip_intensity(
    image: sitk.Image, lower: float, upper: float
) -> sitk.Image:
    """Clip image grey level intensities to specified range.

    The grey level intensities in the resulting image will fall in the range
    [lower, upper].

    Parameters
    ----------
    image
        The intensity image to clip.

    lower
        The lower bound on grey level intensity. Voxels with lower intensity
        will be set to this value.

    upper
        The upper bound on grey level intensity. Voxels with higer intensity
        will be set to this value.

    Returns
    -------
    sitk.Image
        The clipped intensity image.
    """
    return sitk.Clamp(image, image.GetPixelID(), lower, upper)


def window_intensity(
    image: sitk.Image, window: float, level: float
) -> sitk.Image:
    """Restrict image grey level intensities to a given window and level.

    The grey level intensities in the resulting image will fall in the range
    [level - window / 2, level + window / 2].

    Parameters
    ----------
    image
        The intensity image to window.

    window
        The width of the intensity window.

    level
        The mid-point of the intensity window.

    Returns
    -------
    sitk.Image
        The windowed intensity image
    """
    lower = level - window / 2
    upper = level + window / 2
    return clip_intensity(image, lower, upper)
