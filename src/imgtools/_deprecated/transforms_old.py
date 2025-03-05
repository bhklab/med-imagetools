from typing import Any, Optional, Sequence, Union, Callable
from dataclasses import dataclass

import numpy as np
import SimpleITK as sitk
from ..transforms.base_transform import BaseTransform
from ..transforms.functional import (
    clip_intensity,
    resample,
    resize,
    rotate,
    window_intensity,
    zoom,
)

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
    output_size: Optional[Sequence[float]] = None

    def __call__(
        self, image: sitk.Image, ref: None | sitk.Image
    ) -> sitk.Image:
        """Resample image using a specified spacing.
        
        If a reference image is provided, its spacing is used for resampling; otherwise, the transform's
        default spacing is applied. The image is resampled using the instance's interpolation, anti-aliasing,
        anti-alias sigma, transformation, and output size settings.
        
        Parameters:
            image (sitk.Image): The image to be resampled.
            ref (Optional[sitk.Image]): A reference image whose spacing is used if provided.
        
        Returns:
            sitk.Image: The resampled image.
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

    size: Union[int, Sequence[int], np.ndarray]
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

    scale_factor: Union[float, Sequence[float]]
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

    rotation_centre: Sequence[float]
    angles: Union[float, Sequence[float]]
    interpolation: str = "linear"

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
        """
        Rotates an image in-plane about its center.
        
        Calculates the image's center (by halving its dimensions) and rotates it by the
        stored angle using the specified interpolation method. Returns a new image with
        the rotation applied.
        
        Parameters:
            image: sitk.Image
                The input image to be rotated.
        
        Returns:
            sitk.Image: The rotated image.
        """

        image_size = np.array(image.GetSize())
        image_centre = image_size // 2
        angles = (0.0, 0.0, self.angle)
        return rotate(
            image,
            rotation_centre=image_centre.tolist(),
            angles=angles,
            interpolation=self.interpolation,
        )


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
        """
        Clips image intensity values to a specified range.
        
        Parameters
        ----------
        image
            The input SimpleITK image whose intensities will be limited between the 
            specified lower and upper bounds.
        
        Returns
        -------
        sitk.Image
            The resulting image with intensities clipped accordingly.
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
        """
        Restricts image intensities to a specified window and level.
        
        Parameters
        ----------
        image : sitk.Image
            The input intensity image to process.
        
        Returns
        -------
        sitk.Image
            The image with intensity values clipped according to the window and level.
        """

        return window_intensity(image, self.window, self.level)


# Lambda transforms
class SimpleITKFilter(BaseTransform):
    """SimpleITKFilter operation class:
    A callable class that accepts an sitk.ImageFilter object to add a filter to an image.

    To instantiate:
        obj = SimpleITKFilter(sitk_filter, *execute_args)
    To call:
        result = obj(image)

    Parameters
    ----------
    sitk_filter
        An ImageFilter object in sitk library.

    execute_args, optional
        Any arguments to be passed to the Execute() function of the selected ImageFilter object.
    """

    def __init__(
        self, sitk_filter: sitk.ImageFilter, *execute_args: Optional[Any]
    ):
        """
        Initializes a SimpleITKFilter instance.
        
        Stores the provided SimpleITK filter and any additional arguments for later use when
        applying the filter to an image.
        
        Args:
            sitk_filter: A SimpleITK filter (sitk.ImageFilter) to be applied to images.
            *execute_args: Additional positional arguments for the filter's execution.
        """
        self.sitk_filter = sitk_filter
        self.execute_args = execute_args

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """
        Apply the SimpleITK filter to an image.
        
        Executes the configured SimpleITK image filter on the provided image using any additional execution arguments,
        and returns the filtered result.
        
        Parameters:
            image (sitk.Image): The image to be processed.
        
        Returns:
            sitk.Image: The image after applying the filter.
        """
        return self.sitk_filter.Execute(image, *self.execute_args)


class ImageFunction(BaseTransform):
    """ImageFunction operation class:
    A callable class that takens in a function to be used to process an image,
    and executes it.

    To instantiate:
        obj = ImageFunction(function, copy_geometry, **kwargs)
    To call:
        result = obj(image)

    Parameters
    ----------
    function
        A function to be used for image processing.
        This function needs to have the following signature:
        - function(image: sitk.Image, **args)
        - The first argument needs to be an sitkImage, followed by optional arguments.

    copy_geometry, optional
        An optional argument to specify whether information about the image should be copied to the
        resulting image. Set to be true as a default.

    kwargs, optional
        Any number of arguements used in the given function.
    """

    def __init__(
        self,
        function: Callable[..., sitk.Image],
        copy_geometry: bool = True,
        **kwargs: Optional[Any],
    ):
        """
        Initializes an ImageFunction instance.
        
        This transformation processes sitk.Image objects using a user-defined callable.
        The provided function should accept a sitk.Image (and optionally additional
        keyword arguments) and return a processed sitk.Image. If copy_geometry is True,
        the geometry of the input image will be preserved in the output image.
        
        Args:
            function: A callable that takes a sitk.Image (and optionally keyword arguments)
                and returns a modified sitk.Image.
            copy_geometry: If True, transfers the input image's geometric metadata to the
                resulting image.
            kwargs: Additional keyword arguments to pass to the function.
        """
        self.function = function
        self.copy_geometry = copy_geometry
        self.kwargs = kwargs

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """
        Process a SimpleITK image using a specified function.
        
        Applies the user-provided function to the input image with any preset keyword arguments.
        If geometry copying is enabled, the spatial metadata from the input image is transferred
        to the processed image.
        
        Parameters
        ----------
        image : sitk.Image
            The SimpleITK image to be processed.
        
        Returns
        -------
        sitk.Image
            The image after processing and optional geometry transfer.
        """

        result = self.function(image, **self.kwargs)
        if self.copy_geometry:
            result.CopyInformation(image)
        return result
