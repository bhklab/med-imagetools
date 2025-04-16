from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
import SimpleITK as sitk

from imgtools.coretypes import Size3D

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
    """Base class for spatial transforms.

    Spatial transforms modify the spatial properties of an image,
    such as spacing, size, or orientation.

    All spatial transforms support an optional reference image parameter
    in their __call__ method.

    Examples
    --------
    >>> # This is an abstract base class and cannot be instantiated directly.
    >>> # Use one of its subclasses like Resample, Resize, etc.
    """

    def supports_reference(self) -> bool:
        """Return whether this transform supports reference images.

        Returns
        -------
        bool
            Always True for spatial transforms.
        """
        return True


@dataclass
class Resample(SpatialTransform):
    """Resample operation class.

    A callable class that resamples image to a given spacing, optionally
    applying a transformation.

    Parameters
    ----------
    spacing : float | Sequence[float] | np.ndarray
        The new image spacing. If float, assumes the same spacing in all
        directions. Alternatively, a sequence of floats can be passed to
        specify spacing along each dimension. Passing 0 at any position will
        keep the original spacing along that dimension (useful for in-plane
        resampling).
    interpolation : str, optional
        The interpolation method to use. Valid options are:
        - "linear" for bi/trilinear interpolation (default)
        - "nearest" for nearest neighbour interpolation
        - "bspline" for order-3 b-spline interpolation
    anti_alias : bool, optional
        Whether to smooth the image with a Gaussian kernel before resampling.
        Only used when downsampling, i.e. when `spacing < image.GetSpacing()`.
        This should be used to avoid aliasing artifacts.
    anti_alias_sigma : float | None, optional
        The standard deviation of the Gaussian kernel used for anti-aliasing.
    transform : sitk.Transform | None, optional
        Transform to apply to input coordinates when resampling. If None,
        defaults to identity transformation.
    output_size : list[float] | None, optional
        Size of the output image. If None, it is computed to preserve the
        whole extent of the input image.

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> from imgtools.datasets.sample_images import (
    ...     create_sphere_image,
    ... )
    >>> from imgtools.transforms import Resample
    >>> # Create a test image (50x50x25) with 2.0mm spacing
    >>> image = create_sphere_image(
    ...     size=(50, 50, 25), spacing=(2.0, 2.0, 2.0)
    ... )
    >>> # Create resample transform to change to 1.0mm isotropic spacing
    >>> resampler = Resample(spacing=1.0)
    >>> resampled_image = resampler(image)
    >>> print(f"Original size: {image.GetSize()}")
    Original size: (50, 50, 25)
    >>> print(f"Original spacing: {image.GetSpacing()}")
    Original spacing: (2.0, 2.0, 2.0)
    >>> print(
    ...     f"Resampled size: {resampled_image.GetSize()}"
    ... )
    Resampled size: (100, 100, 50)
    >>> print(
    ...     f"Resampled spacing: {resampled_image.GetSpacing()}"
    ... )
    Resampled spacing: (1.0, 1.0, 1.0)
    >>> # Create resample transform with reference image
    >>> ref_image = create_sphere_image(
    ...     size=(100, 100, 100), spacing=(1.5, 1.5, 1.5)
    ... )
    >>> resampled_to_ref = resampler(
    ...     image, ref=ref_image
    ... )
    >>> print(
    ...     f"Reference-based resampling output spacing: {resampled_to_ref.GetSpacing()}"
    ... )
    Reference-based resampling output spacing: (1.5, 1.5, 1.5)
    """

    spacing: float | Sequence[float] | np.ndarray
    interpolation: str = "linear"
    anti_alias: bool = True
    anti_alias_sigma: float | None = None
    transform: sitk.Transform | None = None
    output_size: list[float] | None = None

    def __call__(
        self, image: sitk.Image, ref: sitk.Image | None = None
    ) -> sitk.Image:
        """Resample an image to a designated spacing.

        If a reference image is provided, its spacing is used for resampling;
        otherwise, the object's preset spacing is applied. The method uses the
        configured interpolation, anti-aliasing, and transformation settings
        to produce the resampled image.

        Parameters
        ----------
        image : sitk.Image
            The image to resample.
        ref : sitk.Image | None, optional
            An optional reference image whose spacing is used if provided.

        Returns
        -------
        sitk.Image
            The resampled image.
        """

        # whether or not a reference image is provided
        # spacing = ref.GetSpacing() if ref is not None else self.spacing
        if isinstance(ref, sitk.Image):
            return sitk.Resample(image, ref)
        else:
            spacing_list = (
                list(self.spacing)
                if isinstance(self.spacing, (tuple, Sequence))
                else self.spacing
            )

            return resample(
                image,
                spacing=spacing_list,
                interpolation=self.interpolation,
                anti_alias=self.anti_alias,
                anti_alias_sigma=self.anti_alias_sigma,
                transform=self.transform,
                output_size=self.output_size,
            )


@dataclass
class Resize(SpatialTransform):
    """Resize operation class.

    A callable class that resizes image to a given size by resampling
    coordinates.

    Parameters
    ----------
    size : int | list[int] | np.ndarray
        The new image size. If float, assumes the same size in all directions.
        Alternatively, a sequence of floats can be passed to specify size along
        each dimension. Passing 0 at any position will keep the original
        size along that dimension.
    interpolation : str, optional
        The interpolation method to use. Valid options are:
        - "linear" for bi/trilinear interpolation (default)
        - "nearest" for nearest neighbour interpolation
        - "bspline" for order-3 b-spline interpolation
    anti_alias : bool, optional
        Whether to smooth the image with a Gaussian kernel before resampling.
        Only used when downsampling, i.e. when `size < image.GetSize()`.
        This should be used to avoid aliasing artifacts.
    anti_alias_sigma : float | None, optional
        The standard deviation of the Gaussian kernel used for anti-aliasing.

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> from imgtools.datasets.sample_images import (
    ...     create_gradient_image,
    ... )
    >>> from imgtools.transforms import Resize
    >>> # Create a test image (100x150x50)
    >>> image = create_gradient_image(
    ...     size=(100, 150, 50), direction="radial"
    ... )
    >>> # Resize to uniform dimensions (64x64x64)
    >>> resizer = Resize(size=64)
    >>> resized_image = resizer(image)
    >>> print(f"Original size: {image.GetSize()}")
    Original size: (100, 150, 50)
    >>> print(f"Resized to: {resized_image.GetSize()}")
    Resized to: (64, 64, 64)
    >>> # Resize only first two dimensions
    >>> resizer_2d = Resize(size=[50, 50, 0])
    >>> resized_2d = resizer_2d(image)
    >>> print(
    ...     f"Partially resized: {resized_2d.GetSize()}"
    ... )
    Partially resized: (50, 50, 50)
    """

    size: int | list[int] | np.ndarray
    interpolation: str = "linear"
    anti_alias: bool = True
    anti_alias_sigma: float | None = None

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """Resize the input image to the configured dimensions.

        Uses the specified size, interpolation, and anti-alias settings to
        resample the image and generate a resized output.

        Parameters
        ----------
        image : sitk.Image
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
            anti_alias=self.anti_alias,
            anti_alias_sigma=self.anti_alias_sigma,
        )


@dataclass
class Zoom(SpatialTransform):
    """Zoom operation class.

    A callable class that rescales image, preserving its spatial extent.

    The rescaled image will have the same spatial extent (size) but will be
    rescaled by `scale_factor` in each dimension. Alternatively, a separate
    scale factor for each dimension can be specified by passing a sequence
    of floats.

    Parameters
    ----------
    scale_factor : float | list[float]
        If float, each dimension will be scaled by that factor. If tuple, each
        dimension will be scaled by the corresponding element.
    interpolation : str, optional
        The interpolation method to use. Valid options are:
        - "linear" for bi/trilinear interpolation (default)
        - "nearest" for nearest neighbour interpolation
        - "bspline" for order-3 b-spline interpolation
    anti_alias : bool, optional
        Whether to smooth the image with a Gaussian kernel before resampling.
        Only used when downsampling, i.e. when `size < image.GetSize()`.
        This should be used to avoid aliasing artifacts.
    anti_alias_sigma : float | None, optional
        The standard deviation of the Gaussian kernel used for anti-aliasing.

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> import numpy as np
    >>> from imgtools.datasets.sample_images import (
    ...     create_grid_image,
    ... )
    >>> from imgtools.transforms import Zoom
    >>> # Create a test image (64x64x64) with a grid pattern
    >>> image = create_grid_image(grid_spacing=8)
    >>> # Create zoom with factor 2 (zooming in, grid lines will appear thinner)
    >>> zoomer = Zoom(scale_factor=2.0)
    >>> zoomed_in = zoomer(image)
    >>> print(f"Original size: {image.GetSize()}")
    Original size: (64, 64, 64)
    >>> print(
    ...     f"Zoomed size (unchanged): {zoomed_in.GetSize()}"
    ... )
    Zoomed size (unchanged): (64, 64, 64)
    >>> print(f"Original spacing: {image.GetSpacing()}")
    Original spacing: (1.0, 1.0, 1.0)
    >>> print(
    ...     f"Zoomed spacing: {zoomed_in.GetSpacing()}"
    ... )
    Zoomed spacing: (1.0, 1.0, 1.0)
    >>> # Anisotropic zoom (different factors per dimension)
    >>> aniso_zoomer = Zoom(scale_factor=[0.5, 1.0, 2.0])
    >>> aniso_zoomed = aniso_zoomer(image)
    >>> print("Applied anisotropic zoom")
    Applied anisotropic zoom
    """

    scale_factor: float | list[float]
    interpolation: str = "linear"
    anti_alias: bool = True
    anti_alias_sigma: float | None = None

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """Rescale image, preserving its spatial extent.

        The rescaled image will have the same spatial extent (size) but will be
        rescaled by `scale_factor` in each dimension. Alternatively, a separate
        scale factor for each dimension can be specified by passing a sequence
        of floats.

        Parameters
        ----------
        image : sitk.Image
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
    """Rotate operation class.

    A callable class that rotates an image around a given centre.

    Parameters
    ----------
    rotation_centre : list[int]
        The centre of rotation in image coordinates.
    angles : float | list[float]
        The angles of rotation around x, y and z axes.
    interpolation : str, optional
        The interpolation method to use. Valid options are:
        - "linear" for bi/trilinear interpolation (default)
        - "nearest" for nearest neighbour interpolation
        - "bspline" for order-3 b-spline interpolation

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> import math
    >>> from imgtools.datasets.sample_images import (
    ...     create_rod_image,
    ... )
    >>> from imgtools.transforms import Rotate
    >>> # Create a test image (64x64x64) with a line along the x-axis
    >>> image = create_rod_image(axis="x")
    >>> # Get the center point for rotation
    >>> center = [32, 32, 32]  # Center of the image
    >>> # Create a rotation transform (45° around z-axis)
    >>> rotator = Rotate(
    ...     rotation_centre=center,
    ...     angles=[0.0, 0.0, math.pi / 4],
    ... )
    >>> rotated = rotator(image)
    >>> print(f"Original size: {image.GetSize()}")
    Original size: (64, 64, 64)
    >>> print(f"Rotated size: {rotated.GetSize()}")
    Rotated size: (64, 64, 64)
    >>> # Multiple angles (rotate around all three axes)
    >>> multi_rotator = Rotate(
    ...     rotation_centre=center,
    ...     angles=[
    ...         math.pi / 6,
    ...         math.pi / 4,
    ...         math.pi / 3,
    ...     ],
    ... )
    >>> multi_rotated = multi_rotator(image)
    >>> print("Applied rotation around all three axes")
    Applied rotation around all three axes
    """

    rotation_centre: list[int]
    angles: float | list[float]
    interpolation: str = "linear"

    # internal variable to store angles as a list after validation
    _angles_list: list[float] = field(init=False)

    def __post_init__(self) -> None:
        """Validate and normalize the rotation angles.

        Converts a single float into a triplet by repeating it for all three
        axes or verifies that a list of three floats was provided. Raises a
        ValueError if the angles attribute does not match these requirements.
        """
        match self.angles:
            case float(one_angle):
                self._angles_list = [one_angle, one_angle, one_angle]
            case [float(x_ang), float(y_ang), float(z_ang)]:
                self._angles_list = [x_ang, y_ang, z_ang]
            case _:
                errmsg = "angles must be a float or a list of 3 floats"
                errmsg += f" but got {self.angles}"
                raise ValueError(errmsg)

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """Rotate an image around a specified center.

        Parameters
        ----------
        image : sitk.Image
            The image to rotate.

        Returns
        -------
        sitk.Image
            The rotated image.
        """
        return rotate(
            image,
            rotation_centre=self.rotation_centre,
            angles=self._angles_list,
            interpolation=self.interpolation,
        )


@dataclass
class InPlaneRotate(SpatialTransform):
    """InPlaneRotate operation class.

    A callable class that rotates an image on a plane.

    Parameters
    ----------
    angle : float
        The angle of rotation.
    interpolation : str, optional
        The interpolation method to use. Valid options are:
        - "linear" for bi/trilinear interpolation (default)
        - "nearest" for nearest neighbour interpolation
        - "bspline" for order-3 b-spline interpolation

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> import math
    >>> from imgtools.datasets.sample_images import (
    ...     create_cross_image,
    ... )
    >>> from imgtools.transforms import InPlaneRotate
    >>> # Create a test image (128x128x32) with a cross pattern
    >>> image = create_cross_image(size=(128, 128, 32))
    >>> # Rotate 45 degrees in-plane (around z-axis)
    >>> rotator = InPlaneRotate(angle=math.pi / 4)
    >>> rotated = rotator(image)
    >>> print(f"Original size: {image.GetSize()}")
    Original size: (128, 128, 32)
    >>> print(f"Rotated size: {rotated.GetSize()}")
    Rotated size: (128, 128, 32)
    >>> # Multiple rotations can be applied sequentially
    >>> rotated_again = rotator(
    ...     rotated
    ... )  # Rotate another 45 degrees
    >>> print(
    ...     "Applied two sequential rotations (total 90 degrees)"
    ... )
    Applied two sequential rotations (total 90 degrees)
    """

    angle: float
    interpolation: str = "linear"

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """Rotate an image in its plane.

        The image is rotated around its geometric center using the instance's
        angle and interpolation settings.

        Parameters
        ----------
        image : sitk.Image
            The image to rotate.

        Returns
        -------
        sitk.Image
            The rotated image.
        """

        image_size = Size3D(image.GetSize())
        image_centre: Size3D = image_size // 2
        angles = [0.0, 0.0, self.angle]
        return rotate(
            image,
            rotation_centre=list(image_centre),
            angles=angles,
            interpolation=self.interpolation,
        )
