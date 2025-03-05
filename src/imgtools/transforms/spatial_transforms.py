from dataclasses import dataclass
from typing import Optional, Sequence, Union

import numpy as np
import SimpleITK as sitk

from .base_transform import BaseTransform
from .functional import (
    resample,
    resize,
    rotate,
    zoom,
)

__all__ = [
    "SpatialTransform",
    "Resample",
    "Resize",
    "Zoom",
    "Rotate",
    "InPlaneRotate",
]
"""
These `Transform` classes perform an operation/transformation on 
a sitk.Image object and returns a modified sitk.Image object.
"""


# Resampling transforms
class SpatialTransform(BaseTransform):
    pass


@dataclass
class Resample(SpatialTransform):
    """Resample operation class:
    A callable class that resamples image to a given spacing, optionally applying a transformation.

    To instantiate:
        obj = Resample(spacing, interpolation, anti_alias, anti_alias_sigma, transform, output_size)

    To call:
        result = obj(image)

    Parameters
    ----------
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
    """

    spacing: Union[float, Sequence[float], np.ndarray]
    interpolation: str = "linear"
    anti_alias: bool = True
    anti_alias_sigma: Optional[float] = None
    transform: Optional[sitk.Transform] = None
    output_size: Optional[list[float]] = None

    def __call__(
        self, image: sitk.Image, ref: None | sitk.Image
    ) -> sitk.Image:
        """Resample callable object:
        Resamples image to a given spacing, optionally applying a transformation..

        Parameters
        ----------
        image
            The image to resample.

        Returns
        -------
        sitk.Image
            The resampled image.
        """

        # whether or not a reference image is provided
        if ref is not None:
            spacing = ref.GetSpacing()
        else:
            spacing = self.spacing

        return resample(
            image,
            spacing=spacing,
            interpolation=self.interpolation,
            anti_alias=self.anti_alias,
            anti_alias_sigma=self.anti_alias_sigma,
            transform=self.transform,
            output_size=self.output_size,
        )


@dataclass
class Resize(SpatialTransform):
    """Resize operation class:
    A callable class that resizes image to a given size by resampling coordinates.

    To instantiate:
        obj = Resize(size, interpolation, anti_alias, anti_alias_sigma)

    To call:
        result = obj(image)

    Parameters
    ----------
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
    """

    size: Union[int, list[int], np.ndarray]
    interpolation: str = "linear"
    anti_alias: bool = True
    anti_alias_sigma: Optional[float] = None

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """Resize callable object: Resizes image to a given size by resampling coordinates.

        Parameters
        ----------
        image
            The image to resize.

        Returns
        -------
        sitk.Image
            The resized image.
        """

        return resize(
            image,
            size=self.size,
            interpolation=self.interpolation,
            anti_alias_sigma=self.anti_alias_sigma,
        )


@dataclass
class Zoom(SpatialTransform):
    """Zoom operation class: A callable class that rescales image, preserving its spatial extent.

    To instantiate:
        obj = Zoom(scale_factor, interpolation, anti_alias, anti_alias_sigma)

    To call:
        result = obj(image)

    The rescaled image will have the same spatial extent (size) but will be
    rescaled by `scale_factor` in each dimension. Alternatively, a separate
    scale factor for each dimension can be specified by passing a sequence
    of floats.

    Parameters
    ----------
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
    """

    scale_factor: Union[float, list[float]]
    interpolation: str = "linear"
    anti_alias: bool = True
    anti_alias_sigma: Optional[float] = None

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """Zoom callable object: Rescales image, preserving its spatial extent.

        The rescaled image will have the same spatial extent (size) but will be
        rescaled by `scale_factor` in each dimension. Alternatively, a separate
        scale factor for each dimension can be specified by passing a sequence
        of floats.

        Parameters
        ----------
        image
            The image to rescale.

        Returns
        -------
        sitk.Image
            The rescaled image.
        """

        return zoom(
            image,
            self.scale_factor,
            interpolation=self.interpolation,
            anti_alias=self.anti_alias,
            anti_alias_sigma=self.anti_alias_sigma,
        )


@dataclass
class Rotate(SpatialTransform):
    """Rotate operation class: A callable class that rotates an image around a given centre.

    To instantiate:
        obj = Rotate(rotation_centre, angles, interpolation)

    To call:
        result = obj(image)

    Parameters
    ----------
    rotation_centre
        The centre of rotation in image coordinates.

    angles
        The angles of rotation around x, y and z axes.

    interpolation, optional
        The interpolation method to use. Valid options are:
        - "linear" for bi/trilinear interpolation (default)
        - "nearest" for nearest neighbour interpolation
        - "bspline" for order-3 b-spline interpolation
    """

    rotation_centre: list[float]
    angles: Union[float, list[float]]
    interpolation: str = "linear"

    def __post_init__(self) -> None:
        if isinstance(self.angles, float):
            self.angles = [self.angles, self.angles, self.angles]

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """Rotate callable object: Rotates an image around a given centre.

        Parameters
        ----------
        image
            The image to rotate.

        Returns
        -------
        sitk.Image
            The rotated image.
        """
        return rotate(
            image,
            rotation_centre=self.rotation_centre,
            angles=self.angles,
            interpolation=self.interpolation,
        )


@dataclass
class InPlaneRotate(SpatialTransform):
    """InPlaneRotate operation class: A callable class that rotates an image on a plane.

    To instantiate:
        obj = InPlaneRotate(angle, interpolation)

    To call:
        result = obj(image)

    Parameters
    ----------
    angle
        The angle of rotation.

    interpolation, optional
        The interpolation method to use. Valid options are:
        - "linear" for bi/trilinear interpolation (default)
        - "nearest" for nearest neighbour interpolation
        - "bspline" for order-3 b-spline interpolation
    """

    angle: float
    interpolation: str = "linear"

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """InPlaneRotate callable object: Rotates an image on a plane.

        Parameters
        ----------
        image
            The image to rotate.

        Returns
        -------
        sitk.Image
            The rotated image.
        """

        image_size = np.array(image.GetSize())
        image_centre = image_size // 2
        angles = [0.0, 0.0, self.angle]
        return rotate(
            image,
            rotation_centre=image_centre.tolist(),
            angles=angles,
            interpolation=self.interpolation,
        )
