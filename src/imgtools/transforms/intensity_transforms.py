from dataclasses import dataclass

import SimpleITK as sitk

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
    pass


@dataclass
class ClipIntensity(IntensityTransform):
    """ClipIntensity operation class:
    A callable class that clips image grey level intensities to specified range.

    To instantiate:
        obj = ClipIntensity(lower, upper)

    To call:
        result = obj(image)

    The grey level intensities in the resulting image will fall in the range
    [lower, upper].

    Parameters
    ----------
    lower
        The lower bound on grey level intensity. Voxels with lower intensity
        will be set to this value.

    upper
        The upper bound on grey level intensity. Voxels with higer intensity
        will be set to this value.
    """

    lower: float
    upper: float

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """ClipIntensity callable object:
        Clips image grey level intensities to specified range.

        Parameters
        ----------
        image
            The intensity image to clip.

        Returns
        -------
        sitk.Image
            The clipped intensity image.
        """
        return clip_intensity(image, self.lower, self.upper)


@dataclass
class WindowIntensity(IntensityTransform):
    """WindowIntensity operation class:
    A callable class that restricts image grey level intensities to a given window and level.

    To instantiate:
        obj = WindowIntensity(window, level)

    To call:
        result = obj(image)

    The grey level intensities in the resulting image will fall in the range
    [level - window / 2, level + window / 2].

    Parameters
    ----------
    window
        The width of the intensity window.

    level
        The mid-point of the intensity window.
    """

    window: float
    level: float

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """WindowIntensity callable object:
        Restricts image grey level intensities to a given window and level.

        Parameters
        ----------
        image
            The intensity image to window.

        Returns
        -------
        sitk.Image
            The windowed intensity image.
        """

        return window_intensity(image, self.window, self.level)
