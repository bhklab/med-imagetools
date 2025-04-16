from dataclasses import dataclass

from SimpleITK import Image

from .base_transform import BaseTransform
from .functional import (
    clip_intensity,
    window_intensity,
)

__all__ = [
    "IntensityTransform",
    "ClipIntensity",
    "WindowIntensity",
]


# Intensity transforms
class IntensityTransform(BaseTransform):
    """Base class for intensity transforms.

    Intensity transforms modify the pixel/voxel intensity values
    of an image without changing its spatial properties.

    All intensity transforms operate on individual pixel/voxel values
    independently, leaving the image dimensions, spacing, and orientation
    unchanged.

    Examples
    --------
    >>> # This is an abstract base class and cannot be instantiated directly.
    >>> # Use one of its subclasses like ClipIntensity or WindowIntensity.
    """

    def supports_reference(self) -> bool:
        """Return whether this transform supports reference images.

        Returns
        -------
        bool
            Always False for intensity transforms.
        """
        return False


@dataclass
class ClipIntensity(IntensityTransform):
    """ClipIntensity operation class.

    A callable class that clips image grey level intensities to specified
    range.

    Parameters
    ----------
    lower : float
        The lower bound on grey level intensity. Voxels with lower intensity
        will be set to this value.
    upper : float
        The upper bound on grey level intensity. Voxels with higer intensity
        will be set to this value.

    Raises
    ------
    ValueError
        If lower bound is greater than upper bound.

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> from imgtools.datasets.sample_images import (
    ...     create_gradient_image,
    ... )
    >>> from imgtools.transforms import ClipIntensity
    >>> # Create a sample image with a wide range of intensity values
    >>> image = create_gradient_image(
    ...     direction="x", min_value=-500, max_value=3000
    ... )
    >>> # Create a clipper to set bone window (250 to 1250)
    >>> clipper = ClipIntensity(lower=250, upper=1250)
    >>> clipped = clipper(image)
    >>> # Verify the results
    >>> stats_original = sitk.StatisticsImageFilter()
    >>> stats_clipped = sitk.StatisticsImageFilter()
    >>> stats_original.Execute(image)
    >>> stats_clipped.Execute(clipped)
    >>> print(
    ...     f"Original range: [{stats_original.GetMinimum():.1f}, {stats_original.GetMaximum():.1f}]"
    ... )
    Original range: [-500.0, 3000.0]
    >>> print(
    ...     f"Clipped range: [{stats_clipped.GetMinimum():.1f}, {stats_clipped.GetMaximum():.1f}]"
    ... )
    Clipped range: [250.0, 1250.0]
    >>> # Values below lower bound are set to lower bound
    >>> print(
    ...     f"Original value at position [0,0]: {image[0, 0, 0]:.1f}"
    ... )
    Original value at position [0,0]: -500.0
    >>> print(
    ...     f"Clipped value at position [0,0]: {clipped[0, 0, 0]:.1f}"
    ... )
    Clipped value at position [0,0]: 250.0
    """

    lower: float
    upper: float

    def __post_init__(self) -> None:
        """Validate that lower bound is less than upper bound."""
        if self.lower > self.upper:
            msg = (
                f"Lower bound ({self.lower}) must be less than or equal to "
                f"upper bound ({self.upper})"
            )
            raise ValueError(msg)

    def __call__(self, image: Image) -> Image:
        """Clip image intensities within a specified range.

        This method processes the input image by resetting pixel values lower
        than the lower bound to the lower value and those above the upper
        bound to the upper value. Values within the range are unchanged.

        Parameters
        ----------
        image : Image
            A SimpleITK image to be intensity-clipped.

        Returns
        -------
        Image
            A SimpleITK image with intensities constrained to the range
            [self.lower, self.upper].
        """
        return clip_intensity(image, self.lower, self.upper)


@dataclass
class WindowIntensity(IntensityTransform):
    """WindowIntensity operation class.

    A callable class that restricts image grey level intensities to a given
    window and level. This is commonly used in medical imaging to enhance
    visibility of specific tissue types (e.g., bone window, lung window in CT).

    The window/level parameters define a range centered at the 'level' value
    with a width of 'window'. All intensities outside this range are clipped.

    Parameters
    ----------
    window : float
        The width of the intensity window. Must be positive.
    level : float
        The mid-point of the intensity window.

    Raises
    ------
    ValueError
        If window width is not positive.

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> from imgtools.datasets.sample_images import (
    ...     create_ct_hounsfield_image,
    ... )
    >>> from imgtools.transforms import WindowIntensity
    >>> # Create a sample CT image with Hounsfield unit range
    >>> image = create_ct_hounsfield_image()
    >>> # Create window/level transform for "bone window" (W=2000, L=400)
    >>> bone_window = WindowIntensity(
    ...     window=2000, level=400
    ... )
    >>> windowed_image = bone_window(image)
    >>> # Verify the results
    >>> stats_original = sitk.StatisticsImageFilter()
    >>> stats_windowed = sitk.StatisticsImageFilter()
    >>> stats_original.Execute(image)
    >>> stats_windowed.Execute(windowed_image)
    >>> print(
    ...     f"Original range: [{stats_original.GetMinimum():.1f}, {stats_original.GetMaximum():.1f}]"
    ... )
    Original range: [-1000.0, 3000.0]
    >>> print(
    ...     f"Window-level range: [{stats_windowed.GetMinimum():.1f}, {stats_windowed.GetMaximum():.1f}]"
    ... )
    Window-level range: [-600.0, 1400.0]
    >>> # Create different window/level for lung tissue (W=1500, L=-600)
    >>> lung_window = WindowIntensity(
    ...     window=1500, level=-600
    ... )
    >>> lung_image = lung_window(image)
    >>> stats_lung = sitk.StatisticsImageFilter()
    >>> stats_lung.Execute(lung_image)
    >>> print(
    ...     f"Lung window range: [{stats_lung.GetMinimum():.1f}, {stats_lung.GetMaximum():.1f}]"
    ... )
    Lung window range: [-1350.0, 150.0]
    """

    window: float
    level: float

    def __post_init__(self) -> None:
        """Validate that window is positive."""
        if self.window <= 0:
            msg = f"Window width must be positive, got {self.window}"
            raise ValueError(msg)

    def __call__(self, image: Image) -> Image:
        """Apply a windowing transform to adjust image intensities.

        Adjusts the input image so that intensities falling outside the range
        defined by [level - window/2, level + window/2] are clipped to the
        corresponding bound.

        Parameters
        ----------
        image : Image
            The input intensity image.

        Returns
        -------
        Image
            The intensity image after applying the windowing transform.
        """

        return window_intensity(image, self.window, self.level)
