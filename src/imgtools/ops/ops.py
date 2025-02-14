from typing import Any, Dict, List, Optional, Sequence, Tuple, TypeVar, Union

import numpy as np
import SimpleITK as sitk

from imgtools.io.loaders import (
    BaseLoader,
)
from imgtools.io.writers import (
    BaseWriter,
)
from imgtools.modules import Segmentation, StructureSet, map_over_labels
from imgtools.ops.functional import (
    bounding_box,
    centroid,
    clip_intensity,
    crop,
    crop_to_mask_bounding_box,
    image_statistics,
    min_max_scale,
    resample,
    resize,
    rotate,
    standard_scale,
    window_intensity,
    zoom,
)

LoaderFunction = TypeVar("LoaderFunction")
ImageFilter = TypeVar("ImageFilter")
Function = TypeVar("Function")


# Base class
class BaseOp:
    def __call__(self, *args, **kwargs):
        raise NotImplementedError

    def __repr__(self):
        attrs = [
            (k, v) for k, v in self.__dict__.items() if not k.startswith("_")
        ]
        attrs = [
            (k, f"'{v}'") if isinstance(v, str) else (k, v) for k, v in attrs
        ]
        args = ", ".join(f"{k}={v}" for k, v in attrs)
        return f"{self.__class__.__name__}({args})"


# Input/output
class BaseInput(BaseOp):
    def __init__(self, loader):
        if not isinstance(loader, BaseLoader):
            raise ValueError(
                f"loader must be a subclass of io.BaseLoader, got {type(loader)}"
            )
        self._loader = loader

    def __call__(self, key):
        inputs = self._loader.get(key)
        return inputs


class BaseOutput(BaseOp):
    def __init__(self, writer):
        if not isinstance(writer, BaseWriter):
            raise ValueError(
                f"writer must be a subclass of io.BaseWriter, got {type(writer)}"
            )
        self._writer = writer

    def __call__(self, key, *args, **kwargs):
        self._writer.put(key, *args, **kwargs)


# Resampling ops
class Resample(BaseOp):
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

    def __init__(
        self,
        spacing: Union[float, Sequence[float], np.ndarray],
        interpolation: str = "linear",
        anti_alias: bool = True,
        anti_alias_sigma: Optional[float] = None,
        transform: Optional[sitk.Transform] = None,
        output_size: Optional[Sequence[float]] = None,
    ):
        self.spacing = spacing
        self.interpolation = interpolation
        self.anti_alias = anti_alias
        self.anti_alias_sigma = anti_alias_sigma
        self.transform = transform
        self.output_size = output_size

    def __call__(self, image: sitk.Image) -> sitk.Image:
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

        return resample(
            image,
            spacing=self.spacing,
            interpolation=self.interpolation,
            anti_alias=self.anti_alias,
            anti_alias_sigma=self.anti_alias_sigma,
            transform=self.transform,
            output_size=self.output_size,
        )


class Resize(BaseOp):
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

    def __init__(
        self,
        size: Union[int, Sequence[int], np.ndarray],
        interpolation: str = "linear",
        anti_alias: bool = True,
        anti_alias_sigma: Optional[float] = None,
    ):
        self.size = size
        self.interpolation = interpolation
        self.anti_alias = anti_alias
        self.anti_alias_sigma = anti_alias_sigma

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


class Zoom(BaseOp):
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

    def __init__(
        self,
        scale_factor: Union[float, Sequence[float]],
        interpolation: str = "linear",
        anti_alias: bool = True,
        anti_alias_sigma: Optional[float] = None,
    ):
        self.scale_factor = scale_factor
        self.interpolation = interpolation
        self.anti_alias = anti_alias
        self.anti_alias_sigma = anti_alias_sigma

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


class Rotate(BaseOp):
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

    def __init__(
        self,
        rotation_centre: Sequence[float],
        angles: Union[float, Sequence[float]],
        interpolation: str = "linear",
    ):
        self.rotation_centre = rotation_centre
        self.angles = angles
        self.interpolation = interpolation

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


class InPlaneRotate(BaseOp):
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

    def __init__(self, angle: float, interpolation: str = "linear"):
        self.angle = angle
        self.interpolation = interpolation

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
        angles = (0.0, 0.0, self.angle)
        return rotate(
            image,
            rotation_centre=image_centre.tolist(),
            angles=angles,
            interpolation=self.interpolation,
        )


# Cropping & mask ops
class Crop(BaseOp):
    """Crop operation class: A callable class that crops an image to
    the desired size around a given centre.

    To instantiate:
        obj = Crop(crop_centre, size)

    To call:
        result = obj(image)

    Note that the cropped image might be smaller than size in a particular
    direction if the cropping window exceeds image boundaries.

    Parameters
    ----------

    crop_centre
        The centre of the cropping window in image coordinates.

    size
        The size of the cropping window along each dimension in pixels. If
        float, assumes the same size in all directions. Alternatively, a
        sequence of floats can be passed to specify size along x, y and z
        dimensions. Passing 0 at any position will keep the original size along
        that dimension.
    """

    def __init__(
        self,
        crop_centre: Sequence[float],
        size: Union[int, Sequence[int], np.ndarray],
    ):
        self.crop_centre = crop_centre
        self.size = size

    def __call__(self, image) -> sitk.Image:
        """Crop callable object: Crops an image to the desired size around a given centre.

        Note that the cropped image might be smaller than size in a particular
        direction if the cropping window exceeds image boundaries.

        Parameters
        ----------
        image
            The image to crop.

        Returns
        -------
        sitk.Image
            The cropped image.
        """

        return crop(image, crop_centre=self.crop_centre, size=self.size)


class CentreCrop(BaseOp):
    """CentreCrop operation class: A callable class that crops an image to the desired size
    around the centre of an image.

    To instantiate:
        obj = CentreCrop(size)

    To call:
        result = obj(image)

    Note that the cropped image might be smaller than size in a particular
    direction if the cropping window exceeds image boundaries.

    Parameters
    ----------
    size
        The size of the cropping window along each dimension in pixels. If
        float, assumes the same size in all directions. Alternatively, a
        sequence of floats can be passed to specify size along x, y and z
        dimensions. Passing 0 at any position will keep the original size along
        that dimension.
    """

    def __init__(self, size: Union[int, Sequence[int]]):
        self.size = size

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """CentreCrop callable object: Crops an image to the desired size
        around the centre of an image.

        Note that the cropped image might be smaller than size in a particular
        direction if the cropping window exceeds image boundaries.

        Parameters
        ----------
        image
            The image to crop.

        Returns
        -------
        sitk.Image
            The cropped image.
        """
        image_size = np.array(image.GetSize())
        image_centre = image_size // 2
        return crop(image, crop_centre=image_centre, size=self.size)


class BoundingBox(BaseOp):
    """BoundingBox opetation class: A callable class that find the axis-aligned
    bounding box of a region descriibed by a segmentation mask.

    To instantiate:
        obj = BoundingBox()

    To call:
        result = obj(mask, label)
    """

    def __call__(
        self, mask: sitk.Image, label: int = 1
    ) -> Tuple[Tuple, Tuple]:
        """BoundingBox callable object: Find the axis-aligned
        bounding box of a region descriibed by a segmentation mask.

        Parameters
        ----------
        mask
            Segmentation mask describing the region of interest. Can be an image of
            type unsigned int representing a label map or `segmentation.Segmentation`.

        label, optional
            Label to use when computing bounding box if segmentation mask contains
            more than 1 labelled region.

        Returns
        -------
        tuple of tuples
            The bounding box location and size. The first tuple gives the
            coordinates of the corner closest to the origin and the second
            gives the size in pixels along each dimension.
        """

        return bounding_box(mask, label=label)


class Centroid(BaseOp):
    """Centroid operation class: A callable class that finds the centroid of
    a labelled region specified by a segmentation mask.

    To instantiate:
        obj = Centroid(world_coordinates)

    To call:
        result = obj(mask, label)

    Parameters
    ----------
    world_coordinates, optional
        If True, return centroid in world coordinates, otherwise in image
        (voxel) coordinates (default).
    """

    def __init__(self, world_coordinates: bool = False):
        self.world_coordinates = world_coordinates

    def __call__(self, mask: sitk.Image, label: Optional[int] = 1) -> tuple:
        """Centroid callable object: Finds the centroid of
        a labelled region specified by a segmentation mask.

        Parameters
        ----------
        mask
            Segmentation mask describing the region of interest. Can be an image of
            type unsigned int representing a label map or `segmentation.Segmentation`.

        label, optional
            Label to use when computing the centroid if segmentation mask contains
            more than 1 labelled region.

        Returns
        -------
        tuple
            The centroid coordinates.
        """

        return centroid(
            mask, label=label, world_coordinates=self.world_coordinates
        )


class CropToMaskBoundingBox(BaseOp):
    """CropToMaskBoundingBox opetation class:
    A callable class that crops the image using the bounding box of a region of interest specified
    by a segmentation mask.

    To instantiate:
        obj = CropToMaskBoundingBox(margin)

    To call:
        result = obj(image, mask, label)

    Parameters
    ----------
    margin
        A margin that will be added to each dimension when cropping. If int,
        add the same margin to each dimension. A sequence of ints can also be
        passed to specify the margin separately along each dimension.
    """

    def __init__(self, margin: Union[int, Sequence[int], np.ndarray]):
        self.margin = margin

    def __call__(
        self,
        image: sitk.Image,
        mask: Union[int, Sequence[int], np.ndarray] = None,
        label: Optional[int] = 1,
    ) -> Tuple[sitk.Image]:
        """CropToMaskBoundingBox callable object:
        Crops the image using the bounding box of a region of interest specified
        by a segmentation mask.

        Parameters
        ----------
        image
            The image to crop.

        mask
            Segmentation mask describing the region of interest. Can be an image of
            type unsigned int representing a label map or `segmentation.Segmentation`.

        label, optional
            Label to use when computing the centroid if segmentation mask contains
            more than 1 labelled region.

        Returns
        -------
        tuple of sitk.Image
            The cropped image and mask.
        """

        return crop_to_mask_bounding_box(
            image, mask, margin=self.margin, label=label
        )


# Intensity ops
class ClipIntensity(BaseOp):
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

    def __init__(self, lower: float, upper: float):
        self.lower = lower
        self.upper = upper

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


class WindowIntensity(BaseOp):
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

    def __init__(self, window: float, level: float):
        self.window = window
        self.level = level

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


class ImageStatistics(BaseOp):
    """ImageStatistics operation class:
    A callable class that computes the intensity statistics of an image.

    To instantiate:
        obj = ImageStatistics()

    To call:
        result = obj(image, mask, label)

    Returns the minimum, maximum, sum, mean, variance and standard deviation
    of image intensities.
    This function also supports computing the statistics in a specific
    region of interest if `mask` and `label` are passed.
    """

    def __call__(
        self,
        image: sitk.Image,
        mask: Optional[sitk.Image] = None,
        label: Optional[int] = 1,
    ) -> float:
        """ImageStatistics callable object:
        Computes the intensity statistics of an image.

        Returns the minimum, maximum, sum, mean, variance and standard deviation
        of image intensities.
        This function also supports computing the statistics in a specific
        region of interest if `mask` and `label` are passed.

        Parameters
        ----------
        image
            The image used to compute the statistics.

        mask, optional
            Segmentation mask specifying a region of interest used in computation.
            Can be an image of type unsigned int representing a label map or
            `segmentation.Segmentation`. Only voxels falling within the ROI will
            be considered. If None, use the whole image.

        label, optional
            Label to use when computing the statistics if segmentation mask contains
            more than 1 labelled region.

        Returns
        -------
        collections.namedtuple
            The computed intensity statistics in the image or region.
        """

        return image_statistics(image, mask, label=label)


class StandardScale(BaseOp):
    """StandardScale operation class:
    A callable class that rescales image intensities by subtracting
    the mean and dividing by standard deviation.

    To instantiate:
        obj = StandardScale(rescale_mean, rescale_std)
    To call
        result = obj(image, mask, label)

    If `rescale_mean` and `rescale_std` are None, image mean and standard
    deviation will be used, i.e. the resulting image intensities will have
    0 mean and unit variance. Alternatively, a specific mean and standard
    deviation can be passed to e.g. standardize a whole dataset of images.
    If a segmentation mask is passed, only the voxels falling within the mask
    will be considered when computing the statistics. However, the whole image
    will still be normalized using the computed values.

    Parameters
    ----------

    rescale_mean, optional
        The mean intensity used in rescaling. If None, image mean will be used.

    rescale_std, optional
        The standard deviation used in rescaling. If None, image standard
        deviation will be used.
    """

    def __init__(
        self,
        rescale_mean: Optional[float] = 0.0,
        rescale_std: Optional[float] = 1.0,
    ):
        self.rescale_mean = rescale_mean
        self.rescale_std = rescale_std

    def __call__(
        self,
        image: sitk.Image,
        mask: Optional[sitk.Image] = None,
        label: Optional[int] = 1,
    ) -> sitk.Image:
        """StandardScale callable object:
        A callable class that rescales image intensities by subtracting
        the mean and dividing by standard deviation.

        Parameters
        ----------
        image
            sitk.Image object to be rescaled.

        mask, optional
            Segmentation mask specifying a region of interest used in computation.
            Can be an image of type unsigned int representing a label map or
            `segmentation.Segmentation`. Only voxels falling within the ROI will
            be considered. If None, use the whole image.

        label, optional
            Label to use when computing the statistics if segmentation mask contains
            more than 1 labelled region.

        Returns
        -------
        sitk.Image
            The rescaled image.
        """

        return standard_scale(
            image, mask, self.rescale_mean, self.rescale_std, label
        )


class MinMaxScale(BaseOp):
    """MinMaxScale operation class:
    A callable class that rescales image intensities to a given minimum and maximum.

    Applies a linear transformation to image intensities such that the minimum
    and maximum intensity values in the resulting image are equal to minimum
    (default 0) and maximum (default 1) respectively.

    To instantiante:
        obj = MinMaxScale(minimum, maximum)
    To call:
        result = obj(image)

    Parameters
    ----------

    minimum, optional
        The minimum intensity in the rescaled image.

    maximum, optional
        The maximum intensity in the rescaled image.
    """

    def __init__(self, minimum: float, maximum: float):
        self.minimum = minimum
        self.maximum = maximum

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """MinMaxScale callable object:
        Rescales image intensities to a given minimum and maximum.

        Applies a linear transformation to image intensities such that the minimum
        and maximum intensity values in the resulting image are equal to minimum
        (default 0) and maximum (default 1) respectively.

        Parameters
        ----------
        image
            sitk.Image object to be rescaled.

        Returns
        -------
        sitk.Image
            The rescaled image.
        """
        return min_max_scale(image, self.minimum, self.maximum)


# Lambda ops


class SimpleITKFilter(BaseOp):
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

    def __init__(self, sitk_filter: ImageFilter, *execute_args: Optional[Any]):
        self.sitk_filter = sitk_filter
        self.execute_args = execute_args

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """SimpleITKFilter callable object:
        A callable class that uses an sitk.ImageFilter object to add a filter to an image.

        Parameters
        ----------
        image
            sitk.Image object to be processed.

        Returns
        -------
        sitk.Image
            The processed image with a given filter.
        """
        return self.sitk_filter.Execute(image, *self.execute_args)


class ImageFunction(BaseOp):
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
        function: Function,
        copy_geometry: bool = True,
        **kwargs: Optional[Any],
    ):
        self.function = function
        self.copy_geometry = copy_geometry
        self.kwargs = kwargs

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """ImageFunction callable object:
        Process an image based on a given function.

        Parameters
        ----------
        image
            sitk.Image object to be processed.

        Returns
        -------
        sitk.Image
            The image processed with the given function.
        """

        result = self.function(image, **self.kwargs)
        if self.copy_geometry:
            result.CopyInformation(image)
        return result


# class ArrayFunction(BaseOp):
#     """ArrayFunction operation class:
#     A callable class that takes in a function to be used to process an image from numpy array,
#     and executes it.

#     To instantiate:
#         obj = ArrayFunction(function, copy_geometry, **kwargs)
#     To call:
#         result = obj(image)

#     Parameters
#     ----------
#     function
#         A function to be used for image processing.
#         This function needs to have the following signature:
#         - function(image: sitk.Image, **args)
#         - The first argument needs to be an sitkImage, followed by optional arguments.

#     copy_geometry, optional
#         An optional argument to specify whether information about the image should be copied to the
#         resulting image. Set to be true as a default.

#     kwargs, optional
#         Any number of arguements used in the given function.
#     """

#     def __init__(
#         self, function: Function, copy_geometry: bool = True, **kwargs: Optional[Any]
#     ):
#         self.function = function
#         self.copy_geometry = copy_geometry
#         self.kwargs = kwargs

#     def __call__(self, image: sitk.Image) -> sitk.Image:
#         """ArrayFunction callable object:
#         Processes an image from numpy array.

#         Parameters
#         ----------
#         image
#             sitk.Image object to be processed.

#         Returns
#         -------
#         sitk.Image
#             The image processed with a given function.
#         """

#         array, origin, direction, spacing = image_to_array(image)
#         result = self.function(array, **self.kwargs)
#         if self.copy_geometry:
#             result = array_to_image(result, origin, direction, spacing)
#         else:
#             result = array_to_image(result)
#         return result


# Segmentation ops


class StructureSetToSegmentation(BaseOp):
    """StructureSetToSegmentation operation class:

    A callable class that accepts ROI names, a StructureSet object, and a
    reference image, and returns a Segmentation mask.

    To instantiate:
        obj = StructureSetToSegmentation(roi_names)

    To call:
        mask = obj(structure_set, reference_image)

    Parameters
    ----------
    roi_names : Union[str, List[str], Dict[str, Union[str, List[str]]], None]
        ROI names or patterns to convert to segmentation:
        - `None` (default): All ROIs will be loaded
        - `str`: A single pattern (regex) to match ROI names.
        - `List[str]`: A list of patterns where each matches ROI names.
        - `Dict[str, str | List[str]]`: A dictionary where each key maps to a
          pattern (or list of patterns). The matched names are grouped under
          the same label.
        Both full names and case-insensitive regular expressions are allowed.
    continuous : bool, default=True
        Flag passed to 'physical_points_to_idxs' in 'StructureSet.to_segmentation'.
        Resolves errors caused by ContinuousIndex > Index.

    Notes
    -----
    If `roi_names` contains lists of strings, each matching
    name within a sublist will be assigned the same label. This means
    that `roi_names=['pat']` and `roi_names=[['pat']]` can lead
    to different label assignments, depending on how many ROI names
    match the pattern. E.g. if `self.roi_names = ['fooa', 'foob']`,
    passing `roi_names=['foo(a|b)']` will result in a segmentation with
    two labels, but passing `roi_names=[['foo(a|b)']]` will result in
    one label for both `'fooa'` and `'foob'`.

    If `roi_names` is kept empty ([]), the pipeline will process all ROIs/contours
    found according to their original names.

    In general, the exact ordering of the returned labels cannot be
    guaranteed (unless all patterns in `roi_names` can only match
    a single name or are lists of strings).

    """

    def __init__(
        self,
        roi_names: Union[
            str, List[str], Dict[str, Union[str, List[str]]], None
        ] = None,
        continuous: bool = True,
    ):
        """Initialize the op."""
        self.roi_names = roi_names
        self.continuous = continuous

    def __call__(
        self,
        structure_set: StructureSet,
        reference_image: sitk.Image,
        existing_roi_indices: Dict[str, int],
        ignore_missing_regex: bool,
        roi_select_first: bool = False,
        roi_separate: bool = False,
    ) -> Segmentation | None:
        """Convert the structure set to a Segmentation object.

        Parameters
        ----------
        structure_set
            The structure set to convert.
        reference_image
            Image used as reference geometry.

        Returns
        -------
        Segmentation | None
            The segmentation object.
        """
        return structure_set.to_segmentation(
            reference_image,
            roi_names=self.roi_names,
            continuous=self.continuous,
            existing_roi_indices=existing_roi_indices,
            ignore_missing_regex=ignore_missing_regex,
            roi_select_first=roi_select_first,
            roi_separate=roi_separate,
        )


# class FilterSegmentation:
#     """FilterSegmentation operation class:
#     A callable class that accepts ROI names, a Segmentation mask with all labels
#     and returns only the desired Segmentation masks based on accepted ROI names.

#     To instantiate:
#         obj = StructureSet(roi_names)
#     To call:
#         mask = obj(structure_set, reference_image)

#     Parameters
#     ----------
#     roi_names
#         List of Region of Interests
#     """

#     def __init__(self, roi_patterns: Dict[str, str], continuous: bool = False):
#         """Initialize the op.

#         Parameters
#         ----------
#         roi_names
#             List of ROI names to export. Both full names and
#             case-insensitive regular expressions are allowed.
#             All labels within one sublist will be assigned
#             the same label.

#         """
#         self.roi_patterns = roi_patterns
#         self.continuous = continuous

#     def _assign_labels(
#         self, names, roi_select_first: bool = False, roi_separate: bool = False
#     ):
#         """
#         Parameters
#         ----
#         roi_select_first
#             Select the first matching ROI/regex for each OAR, no duplicate matches.

#         roi_separate
#             Process each matching ROI/regex as individual masks, instead of consolidating into one mask
#             Each mask will be named ROI_n, where n is the nth regex/name/string.
#         """
#         labels = {}
#         cur_label = 0
#         if names == self.roi_patterns:
#             for i, name in enumerate(self.roi_patterns):
#                 labels[name] = i
#         else:
#             for _, pattern in enumerate(names):
#                 if sorted(names) == sorted(
#                     list(labels.keys())
#                 ):  # checks if all ROIs have already been processed.
#                     break
#                 if isinstance(pattern, str):
#                     for i, name in enumerate(self.roi_names):
#                         if re.fullmatch(pattern, name, flags=re.IGNORECASE):
#                             labels[name] = cur_label
#                             cur_label += 1
#                 else:  # if multiple regex/names to match
#                     matched = False
#                     for subpattern in pattern:
#                         if roi_select_first and matched:
#                             break  # break if roi_select_first and we're matched
#                         for n, name in enumerate(self.roi_names):
#                             if re.fullmatch(subpattern, name, flags=re.IGNORECASE):
#                                 matched = True
#                                 if not roi_separate:
#                                     labels[name] = cur_label
#                                 else:
#                                     labels[f"{name}_{n}"] = cur_label

#                     cur_label += 1
#         return labels

#     def get_mask(self, reference_image, seg, mask, label, idx, continuous):
#         size = seg.GetSize()
#         seg_arr = sitk.GetArrayFromImage(seg)
#         if len(size) == 5:
#             size = size[:-1]
#         elif len(size) == 3:
#             size = size.append(1)

#         idx_seg = (
#             self.roi_names[label] - 1
#         )  # SegmentSequence numbering starts at 1 instead of 0
#         if (
#             size[:-1] == reference_image.GetSize()
#         ):  # Assumes `size` is length of 4: (x, y, z, channels)
#             mask[:, :, :, idx] += seg[:, :, :, idx_seg]
#         else:  # if 2D segmentations on 3D images
#             frame = seg.frame_groups[idx_seg]
#             ref_uid = (
#                 frame.DerivationImageSequence[0]
#                 .SourceImageSequence[0]
#                 .ReferencedSOPInstanceUID
#             )  # unused but references InstanceUID of slice
#             assert ref_uid is not None, "There was no ref_uid"  # dodging linter

#             frame_coords = np.array(frame.PlanePositionSequence[0].ImagePositionPatient)
#             img_coords = physical_points_to_idxs(
#                 reference_image, np.expand_dims(frame_coords, (0, 1))
#             )[0][0]
#             z = img_coords[0]

#             mask[z, :, :, idx] += seg_arr[0, idx_seg, :, :]

#     def __call__(
#         self,
#         reference_image: sitk.Image,
#         seg: Segmentation,
#         existing_roi_indices: Dict[str, int],
#         ignore_missing_regex: bool = False,
#         roi_select_first: bool = False,
#         roi_separate: bool = False,
#     ) -> Segmentation:
#         """Convert the structure set to a Segmentation object.

#         Parameters
#         ----------
#         structure_set
#             The structure set to convert.
#         reference_image
#             Image used as reference geometry.

#         Returns
#         -------
#         Segmentation
#             The segmentation object.
#         """
#         from itertools import groupby

#         # variable name isn't ideal, but follows StructureSet.to_segmentation convention
#         self.roi_names = seg.raw_roi_names
#         labels = {}

#         # `roi_names` in .to_segmentation() method = self.roi_patterns
#         if self.roi_patterns is None or self.roi_patterns == {}:
#             self.roi_patterns = self.roi_names
#             labels = self._assign_labels(
#                 self.roi_patterns, roi_select_first, roi_separate
#             )  # only the ones that match the regex
#         elif isinstance(self.roi_patterns, dict):
#             for name, pattern in self.roi_patterns.items():
#                 if isinstance(pattern, str):
#                     matching_names = list(
#                         self._assign_labels([pattern], roi_select_first).keys()
#                     )
#                     if matching_names:
#                         labels[name] = (
#                             matching_names  # {"GTV": ["GTV1", "GTV2"]} is the result of _assign_labels()
#                         )
#                 elif isinstance(
#                     pattern, list
#                 ):  # for inputs that have multiple patterns for the input, e.g. {"GTV": ["GTV.*", "HTVI.*"]}
#                     labels[name] = []
#                     for pattern_one in pattern:
#                         matching_names = list(
#                             self._assign_labels([pattern_one], roi_select_first).keys()
#                         )
#                         if matching_names:
#                             labels[name].extend(
#                                 matching_names
#                             )  # {"GTV": ["GTV1", "GTV2"]}
#         elif isinstance(
#             self.roi_patterns, list
#         ):  # won't this always trigger after the previous?
#             labels = self._assign_labels(self.roi_patterns, roi_select_first)
#         else:
#             raise ValueError(f"{self.roi_patterns} not expected datatype")
#         logger.debug(f"Found {len(labels)} labels", labels=labels)

#         # removing empty labels from dictionary to prevent processing empty masks
#         all_empty = True
#         for v in labels.values():
#             if v != []:
#                 all_empty = False
#         if all_empty:
#             if not ignore_missing_regex:
#                 raise ValueError(
#                     f"No ROIs matching {self.roi_patterns} found in {self.roi_names}."
#                 )
#             else:
#                 return None

#         labels = {k: v for (k, v) in labels.items() if v != []}
#         size = reference_image.GetSize()[::-1] + (len(labels),)
#         mask = np.zeros(size, dtype=np.uint8)

#         seg_roi_indices = {}
#         if self.roi_patterns != {} and isinstance(self.roi_patterns, dict):
#             for i, (name, label_list) in enumerate(labels.items()):
#                 for label in label_list:
#                     self.get_mask(reference_image, seg, mask, label, i, self.continuous)
#                 seg_roi_indices[name] = i
#         else:
#             for name, label in labels.items():
#                 self.get_mask(reference_image, seg, mask, name, label, self.continuous)
#             seg_roi_indices = {
#                 "_".join(k): v for v, k in groupby(labels, key=lambda x: labels[x])
#             }

#         mask[mask > 1] = 1
#         mask = sitk.GetImageFromArray(mask, isVector=True)
#         mask.CopyInformation(reference_image)
#         return Segmentation(
#             mask,
#             roi_indices=seg_roi_indices,
#             existing_roi_indices=existing_roi_indices,
#             raw_roi_names=labels,
#         )


# class MapOverLabels(BaseOp):
#     """MapOverLabels operation class:

#     To instantiate:
#         obj = MapOverLabels(op, include_background, return_segmentation)
#     To call:
#         mask = obj(segmentation, **kwargs)

#     Parameters
#     ----------
#     op
#         A processing function to be used for the operation.

#     """

#     def __init__(
#         self, op, include_background: bool = False, return_segmentation: bool = True
#     ):
#         self.op = op
#         self.include_background = include_background
#         self.return_seg = return_segmentation

#     def __call__(
#         self, segmentation: Segmentation, **kwargs: Optional[Any]
#     ) -> Segmentation:
#         """MapOverLabels callable object:

#         Parameters
#         ----------
#         include_background
#             Specify whether to include background. Set to be false as a default.

#         return_segmentation
#             Specify whether to return segmentation. Set to be true as a default.

#         **kwargs
#             Arguments used for the processing function.

#         Returns
#         -------
#         Segmentation
#             The segmentation mask.
#         """

#         return map_over_labels(
#             segmentation,
#             self.op,
#             include_background=self.include_background,
#             return_segmentation=self.return_seg,
#             **kwargs,
#         )
