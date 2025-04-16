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
    spacing: float | list[float] | np.ndarray,
    interpolation: str = "linear",
    anti_alias: bool = True,
    anti_alias_sigma: float | list[float] | None = None,
    transform: sitk.Transform | None = None,
    output_size: list[float] | None = None,
) -> sitk.Image:
    """Resample an image to a new spacing with optional transform.

    Resamples the input image using the specified spacing, computing a new
    image size to maintain the original spatial extent unless explicitly set
    via output_size. A transformation can be applied during resampling, and
    Gaussian smoothing is used for anti-aliasing when downsampling.

    Parameters
    ----------
    image : sitk.Image
        The SimpleITK image to be resampled.
    spacing : float | list[float] | np.ndarray
        The desired spacing for each axis. A single float applies to all
        dimensions, while a sequence specifies spacing per axis. Use 0 for any
        axis to retain its original spacing.
    interpolation : str, optional
        The interpolation method to use. Accepted values are "linear",
        "nearest", and "bspline". Defaults to "linear".
    anti_alias : bool, optional
        If True, applies Gaussian smoothing before resampling when downsampling
        to reduce aliasing artifacts. Defaults to True.
    anti_alias_sigma : float | list[float] | None, optional
        The standard deviation for the Gaussian smoothing kernel. If not
        provided, it is automatically computed.
    transform : sitk.Transform | None, optional
        A transformation to apply to the image coordinates during resampling.
        Defaults to the identity transformation if not specified.
    output_size : list[float] | None, optional
        The desired size of the output image. If omitted, the size is
        calculated to preserve the entire extent of the input image.

    Returns
    -------
    sitk.Image
        The resampled image.

    Raises
    ------
    ValueError
        If the specified interpolation method is not supported.

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> import numpy as np
    >>> from imgtools.datasets.sample_images import (
    ...     create_sphere_image,
    ... )
    >>> from imgtools.transforms.functional import (
    ...     resample,
    ... )
    >>> # Create a sample sphere image with 2.0 mm spacing
    >>> image = create_sphere_image(
    ...     spacing=(2.0, 2.0, 2.0)
    ... )
    >>> # Resample to isotropic 1.0 mm spacing
    >>> resampled = resample(image, spacing=1.0)
    >>> print(f"Original spacing: {image.GetSpacing()}")
    Original spacing: (2.0, 2.0, 2.0)
    >>> print(
    ...     f"Resampled spacing: {resampled.GetSpacing()}"
    ... )
    Resampled spacing: (1.0, 1.0, 1.0)
    >>> print(f"Original size: {image.GetSize()}")
    Original size: (64, 64, 64)
    >>> print(f"Resampled size: {resampled.GetSize()}")
    Resampled size: (128, 128, 128)
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
    size: int | list[int] | np.ndarray,
    interpolation: str = "linear",
    anti_alias: bool = True,
    anti_alias_sigma: float | None = None,
) -> sitk.Image:
    """Resize an image to a specified size by resampling its coordinates.

    The function calculates new spacing based on the target size and the
    original image's dimensions. A value of 0 in the size parameter for any
    axis preserves the original size for that dimension.

    Parameters
    ----------
    image : sitk.Image
        The image to be resized.
    size : int | list[int] | np.ndarray
        The target image size. If an integer is provided, the same size is
        applied to all axes. For sequences, a value of 0 for an axis retains
        the original size in that dimension.
    interpolation : str, optional
        The interpolation method to use. Valid options are:
        - "linear" for bi-/trilinear interpolation (default)
        - "nearest" for nearest-neighbor interpolation
        - "bspline" for order-3 b-spline interpolation.
    anti_alias : bool, optional
        If True, apply Gaussian smoothing before resampling when downsampling
        to reduce aliasing artifacts.
    anti_alias_sigma : float | None, optional
        The standard deviation of the Gaussian kernel used for anti-aliasing.

    Returns
    -------
    sitk.Image
        The resized image.

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> from imgtools.datasets.sample_images import (
    ...     create_gradient_image,
    ... )
    >>> from imgtools.transforms.functional import resize
    >>> # Create a sample 3D gradient image (128x128x64)
    >>> image = create_gradient_image(
    ...     size=(128, 128, 64)
    ... )
    >>> # Resize to 64x64x64
    >>> resized = resize(image, [64, 64, 64])
    >>> print(f"Original size: {image.GetSize()}")
    Original size: (128, 128, 64)
    >>> print(f"Resized: {resized.GetSize()}")
    Resized: (64, 64, 64)
    >>> # Resize only the first two dimensions, keeping the third unchanged
    >>> resized_2d = resize(image, [64, 64, 0])
    >>> print(
    ...     f"Partially resized: {resized_2d.GetSize()}"
    ... )
    Partially resized: (64, 64, 64)
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
    scale_factor: float | list[float],
    interpolation: str = "linear",
    anti_alias: bool = True,
    anti_alias_sigma: float | None = None,
) -> sitk.Image:
    """Rescale image, preserving its spatial extent.

    The image is rescaled using the provided scale factor for each dimension
    while maintaining its original spatial extent. A single float applies
    uniformly across all dimensions, whereas a sequence specifies a separate
    factor for each axis.

    Parameters
    ----------
    image : sitk.Image
        The image to rescale.
    scale_factor : float | list[float]
        The scaling factor(s) to apply. A float applies to all dimensions;
        a sequence specifies a factor for each corresponding dimension.
    interpolation : str, optional
        The interpolation method to use. Options include "linear" (default),
        "nearest", and "bspline".
    anti_alias : bool, optional
        Whether to smooth the image using a Gaussian kernel before resampling,
        which helps reduce aliasing artifacts during downsampling.
    anti_alias_sigma : float | None, optional
        The standard deviation for the Gaussian kernel used in anti-aliasing.

    Returns
    -------
    sitk.Image
        The rescaled image with the same spatial extent as the original.

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> from imgtools.datasets.sample_images import (
    ...     create_grid_image,
    ... )
    >>> from imgtools.transforms.functional import zoom
    >>> # Create a sample 3D grid image (100x100x50)
    >>> image = create_grid_image(
    ...     size=(100, 100, 50), grid_spacing=10
    ... )
    >>> # Zoom in by a factor of 2 (grid lines will appear thinner)
    >>> zoomed_in = zoom(image, 2.0)
    >>> print(f"Original size: {image.GetSize()}")
    Original size: (100, 100, 50)
    >>> print(f"Zoomed size: {zoomed_in.GetSize()}")
    Zoomed size: (100, 100, 50)
    >>> print(f"Original spacing: {image.GetSpacing()}")
    Original spacing: (1.0, 1.0, 1.0)
    >>> print(
    ...     f"Zoomed spacing: {zoomed_in.GetSpacing()}"
    ... )
    Zoomed spacing: (1.0, 1.0, 1.0)
    >>> # Zoom out different amounts in each dimension
    >>> zoomed_out = zoom(image, [0.5, 0.5, 1.0])
    >>> print(
    ...     f"Anisotropic zoom spacing: {zoomed_out.GetSpacing()}"
    ... )
    Anisotropic zoom spacing: (1.0, 1.0, 1.0)
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
    rotation_centre: list[int],
    angles: list[float],
    interpolation: str = "linear",
) -> sitk.Image:
    """Rotate an image around a specified center.

    This function applies an Euler rotation to the input image. For 2D images,
    only the first angle in the provided list is used. For 3D images, all three
    angles (for the x, y, and z axes, respectively) are applied.

    Parameters
    ----------
    image : sitk.Image
        The image to rotate.
    rotation_centre : list[int]
        The center of rotation in image coordinates. If provided as a NumPy
        array, it is converted to a list.
    angles : list[float]
        A list of rotation angles in radians. For 2D images, only the first
        value is used. For 3D images, the angles correspond to rotations around
        the x, y, and z axes.
    interpolation : str, optional
        The interpolation method for resampling (e.g., "linear", "nearest").

    Returns
    -------
    sitk.Image
        The rotated image.

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> import math
    >>> from imgtools.datasets.sample_images import (
    ...     create_rod_image,
    ... )
    >>> from imgtools.transforms.functional import rotate
    >>> # Create a sample 3D image with a rod along the x-axis
    >>> image = create_rod_image(axis="x")
    >>> # Get the center of the image
    >>> center = [
    ...     image.GetWidth() // 2,
    ...     image.GetHeight() // 2,
    ...     image.GetDepth() // 2,
    ... ]
    >>> # Rotate 45 degrees around the z-axis (in radians)
    >>> rotated = rotate(
    ...     image, center, [0.0, 0.0, math.pi / 4]
    ... )
    >>> print(f"Original size: {image.GetSize()}")
    Original size: (64, 64, 64)
    >>> print(f"Rotated size: {rotated.GetSize()}")
    Rotated size: (64, 64, 64)
    >>> # Rotate around all axes
    >>> fully_rotated = rotate(
    ...     image,
    ...     center,
    ...     [math.pi / 6, math.pi / 4, math.pi / 3],
    ... )
    >>> print(
    ...     "Applied rotations around x, y, and z axes"
    ... )
    Applied rotations around x, y, and z axes
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
    crop_centre: list[float] | np.ndarray,
    size: int | list[int] | np.ndarray,
) -> sitk.Image:
    """Crop an image to a specified window size about a given center.

    This function extracts a sub-region from the input image centered at the
    provided coordinates. If the cropping window extends beyond the image
    boundaries, the resulting image will be clipped accordingly. A cropping size
    of 0 for any dimension retains the original image extent along that axis.

    Parameters
    ----------
    image : sitk.Image
        The SimpleITK image to crop.
    crop_centre : list[float] | np.ndarray
        The center of the cropping window in image coordinates.
    size : int | list[int] | np.ndarray
        The size of the cropping window in pixels. If an int is provided,
        the same size is applied to all dimensions; a sequence specifies the
        size along each axis. Use 0 to preserve the original size along a
        particular dimension.

    Returns
    -------
    sitk.Image
        The cropped image.

    Raises
    ------
    ValueError
        If the cropping center is outside the image boundaries.

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> from imgtools.datasets.sample_images import (
    ...     create_gradient_image,
    ... )
    >>> from imgtools.transforms.functional import crop
    >>> # Create a sample gradient image
    >>> image = create_gradient_image(
    ...     size=(100, 100, 100), direction="radial"
    ... )
    >>> # Get the center of the image
    >>> center = [
    ...     image.GetWidth() // 2,
    ...     image.GetHeight() // 2,
    ...     image.GetDepth() // 2,
    ... ]
    >>> # Crop a region of 40x50x30 around the center
    >>> cropped = crop(image, center, [40, 50, 30])
    >>> print(f"Original size: {image.GetSize()}")
    Original size: (100, 100, 100)
    >>> print(f"Cropped size: {cropped.GetSize()}")
    Cropped size: (40, 50, 30)
    >>> # Crop while preserving the z-dimension
    >>> cropped_2d = crop(image, center, [40, 50, 0])
    >>> print(
    ...     f"Partially cropped size: {cropped_2d.GetSize()}"
    ... )
    Partially cropped size: (40, 50, 100)
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
    """Clip image intensities to a specified range.

    Adjusts the input image so that all voxel intensity values lie within the
    [lower, upper] range. Values below the lower bound are set to lower, while
    those above the upper bound are set to upper.

    Parameters
    ----------
    image : sitk.Image
        The input intensity image.
    lower : float
        The minimum allowable intensity value.
    upper : float
        The maximum allowable intensity value.

    Returns
    -------
    sitk.Image
        The resulting image with intensity values clipped between lower and upper.

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> from imgtools.datasets.sample_images import (
    ...     create_gradient_image,
    ... )
    >>> from imgtools.transforms.functional import (
    ...     clip_intensity,
    ... )
    >>> # Create a sample image with varying intensities from -2 to 3
    >>> image = create_gradient_image(
    ...     direction="x", min_value=-2.0, max_value=3.0
    ... )
    >>> # Clip intensities between 0.0 and 1.0
    >>> clipped = clip_intensity(image, 0.0, 1.0)
    >>> # Check the results
    >>> original_stats = sitk.StatisticsImageFilter()
    >>> clipped_stats = sitk.StatisticsImageFilter()
    >>> original_stats.Execute(image)
    >>> clipped_stats.Execute(clipped)
    >>> print(
    ...     f"Original range: [{original_stats.GetMinimum():.1f}, {original_stats.GetMaximum():.1f}]"
    ... )
    Original range: [-2.0, 3.0]
    >>> print(
    ...     f"Clipped range: [{clipped_stats.GetMinimum():.1f}, {clipped_stats.GetMaximum():.1f}]"
    ... )
    Clipped range: [0.0, 1.0]
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
    image : sitk.Image
        The intensity image to window.
    window : float
        The width of the intensity window.
    level : float
        The mid-point of the intensity window.

    Returns
    -------
    sitk.Image
        The windowed intensity image

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> from imgtools.datasets.sample_images import (
    ...     create_ct_hounsfield_image,
    ... )
    >>> from imgtools.transforms.functional import (
    ...     window_intensity,
    ... )
    >>> # Create a sample CT image with Hounsfield unit range
    >>> image = create_ct_hounsfield_image()
    >>> # Apply window-level transform (CT bone window: window=2000, level=400)
    >>> bone_window = window_intensity(image, 2000, 400)
    >>> # Apply window-level transform (CT lung window: window=1500, level=-600)
    >>> lung_window = window_intensity(image, 1500, -600)
    >>> # Check the results
    >>> original_stats = sitk.StatisticsImageFilter()
    >>> bone_stats = sitk.StatisticsImageFilter()
    >>> lung_stats = sitk.StatisticsImageFilter()
    >>> original_stats.Execute(image)
    >>> bone_stats.Execute(bone_window)
    >>> lung_stats.Execute(lung_window)
    >>> print(
    ...     f"Original range: [{original_stats.GetMinimum():.1f}, {original_stats.GetMaximum():.1f}]"
    ... )
    Original range: [-1000.0, 3000.0]
    >>> print(
    ...     f"Bone window range: [{bone_stats.GetMinimum():.1f}, {bone_stats.GetMaximum():.1f}]"
    ... )
    Bone window range: [-600.0, 1400.0]
    >>> print(
    ...     f"Lung window range: [{lung_stats.GetMinimum():.1f}, {lung_stats.GetMaximum():.1f}]"
    ... )
    Lung window range: [-1350.0, 150.0]
    """
    lower = level - window / 2
    upper = level + window / 2
    return clip_intensity(image, lower, upper)
