from itertools import chain

import numpy as np
import SimpleITK as sitk

from .functional import *
from ..io import BaseLoader, BaseWriter
from ..utils import image_to_array, array_to_image


class BaseOp:
    def __call__(self, *args, **kwargs):
        raise NotImplementedError

    def __repr__(self):
        attrs = [(k, v) for k, v in self.__dict__.items()
                 if not k.startswith("_")]
        args = ", ".join(f"{k}={v}" for k, v in attrs)
        return f"{self.__class__.__module__}.{self.__class__.__name__}({args})"


class Input(BaseOp):
    def __init__(self, loader):
        if not isinstance(loader, BaseLoader):
            raise ValueError(
                f"loader must be a subclass of io.BaseLoader, got {type(loader)}"
            )
        self.loader = loader

    def __call__(self, key):
        inputs = self.loader.get(key)
        return inputs


class Output(BaseOp):
    def __init__(self, writer):
        if not isinstance(writer, BaseWriter):
            raise ValueError(
                f"writer must be a subclass of io.BaseWriter, got {type(writer)}"
            )
        self.writer = writer

    def __call__(self, key, *args, **kwargs):
        self.writer.put(key, *args, **kwargs)


class Resample(BaseOp):
    def __init__(self,
                 spacing,
                 interpolation="linear",
                 anti_alias=True,
                 anti_alias_sigma=2.,
                 transform=None):
        self.spacing = spacing
        self.interpolation = interpolation
        self.anti_alias = anti_alias
        self.anti_alias_sigma = anti_alias_sigma
        self.transform = transform

    def __call__(self, image):
        return resample(image,
                        spacing=self.spacing,
                        interpolation=self.interpolation,
                        anti_alias=self.anti_alias,
                        anti_alias_sigma=self.anti_alias_sigma,
                        transform=self.transform)


class Resize(BaseOp):
    def __init__(self, size, interpolation="linear", anti_alias=True):
        self.size = size
        self.interpolation = interpolation
        self.anti_alias = anti_alias

    def __call__(self, image):
        return resize(image,
                      new_size=self.size,
                      interpolation=self.interpolation)


class Rotate(BaseOp):
    def __init__(self, rotation_centre, angles, interpolation="linear"):
        self.rotation_centre = rotation_centre
        self.angles = angles
        self.interpolation = interpolation

    def __call__(self, image):
        return rotate(image,
                      rotation_centre=self.rotation_centre,
                      angles=self.angles,
                      interpolation=self.interpolation)


class InPlaneRotate(BaseOp):
    def __init__(self, angle, interpolation="linear"):
        self.angle = angle
        self.interpolation = interpolation

    def __call__(self, image):
        image_size = np.array(image.GetSize())
        image_centre = image_size // 2
        angles = (0., 0., self.angle)
        return rotate(image,
                      rotation_centre=image_centre,
                      angles=angles,
                      interpolation=self.interpolation)


class Crop(BaseOp):
    def __init__(self, crop_centre, size):
        self.crop_centre = crop_centre
        self.size = size

    def __call__(self, image):
        return crop(image, crop_centre=self.crop_centre, size=self.size)


class CentreCrop(BaseOp):
    def __init__(self, size):
        self.size = size

    def __call__(self, image):
        image_size = np.array(image.GetSize())
        image_centre = image_size // 2
        return crop(image, crop_centre=image_centre, size=self.size)


class BoundingBox(BaseOp):
    def __call__(self, mask, label=1):
        return bounding_box(mask, label=label)


class Centroid(BaseOp):
    def __init__(self, world_coordinates=False):
        self.world_coordinates = world_coordinates

    def __call__(self, mask, label=1):
        return centroid(mask,
                        label=label,
                        world_coordiantes=self.world_coordinates)


class CropToMaskBoundingBox(BaseOp):
    def __init__(self, margin):
        self.margin = margin

    def __call__(self, image, mask=None, label=1):
        return crop_to_mask_bounding_box(image,
                                         mask,
                                         margin=self.margin,
                                         label=label)


class ClipIntensity(BaseOp):
    def __init__(self, lower, upper):
        self.lower = lower
        self.upper = upper

    def __call__(self, image):
        return clip_intensity(image, self.lower, self.upper)


class WindowIntensity(BaseOp):
    def __init__(self, window, level):
        self.window = window
        self.level = level

    def __call__(self, image):
        return window_intensity(image, self.window, self.level)


class ImageStatistics(BaseOp):
    def __call__(self, image, mask=None, label=1):
        return image_statistics(image, mask, label=label)


class StandardScale(BaseOp):
    def __init__(self, rescale_mean=0., rescale_std=1.):
        self.rescale_mean = rescale_mean
        self.rescale_std = rescale_std

    def __call__(self, image, mask=None, label=1):
        return standard_scale(image, mask, self.rescale_mean, self.rescale_std,
                              label)


class MinMaxScale(BaseOp):
    def __init__(self, minimum, maximum):
        self.minimum = minimum
        self.maximum = maximum

    def __call__(self, image):
        return min_max_scale(image, self.minimum, self.maximum)


class SimpleITKFilter(BaseOp):
    def __init__(self, sitk_filter, *execute_args):
        self.sitk_filter = sitk_filter
        self.execute_args = execute_args

    def __call__(self, image):
        return self.sitk_filter.Execute(image, *self.execute_args)


class ImageFunction(BaseOp):
    def __init__(self, function, copy_geometry=True, **kwargs):
        self.function = function
        self.copy_geometry = copy_geometry
        self.kwargs = kwargs

    def __call__(self, image):
        result = self.function(image, **self.kwargs)
        if self.copy_geometry:
            result.CopyInformation(image)
        return result


class ArrayFunction(BaseOp):
    def __init__(self, function, copy_geometry=True, **kwargs):
        self.function = function
        self.copy_geometry = copy_geometry
        self.kwargs = kwargs

    def __call__(self, image):
        array, origin, direction, spacing = image_to_array(image)
        result = self.function(array, **self.kwargs)
        if self.copy_geometry:
            result = array_to_image(result, origin, direction, spacing)
        else:
            result = array_to_image(result)
        return result


class StructureSetToMask(BaseOp):
    def __init__(self, roi_names):
        self.roi_names = roi_names

    def __call__(self, structure_set, reference_image):
        return structure_set.to_mask(reference_image, roi_names=self.roi_names)
