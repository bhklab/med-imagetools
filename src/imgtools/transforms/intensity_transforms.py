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
