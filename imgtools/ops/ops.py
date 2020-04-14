from itertools import chain

import numpy as np
import SimpleITK as sitk

from .functional import *
from ..io import BaseLoader, BaseWriter
from ..utils import image_to_array, array_to_image
from ..segmentation import map_over_labels
from ..io import *


# Base class

class BaseOp:
    def __call__(self, *args, **kwargs):
        raise NotImplementedError

    def __repr__(self):
        attrs = [(k, v) for k, v in self.__dict__.items()
                 if not k.startswith("_")]
        args = ", ".join(f"{k}={v}" for k, v in attrs)
        return f"{self.__class__.__module__}.{self.__class__.__name__}({args})"


# Input/output

class BaseInput(BaseOp):
    def __init__(self, loader):
        if not isinstance(loader, BaseLoader):
            raise ValueError(
                f"loader must be a subclass of io.BaseLoader, got {type(loader)}"
            )
        self.loader = loader

    def __call__(self, key):
        inputs = self.loader.get(key)
        return inputs


class BaseOutput(BaseOp):
    def __init__(self, writer):
        if not isinstance(writer, BaseWriter):
            raise ValueError(
                f"writer must be a subclass of io.BaseWriter, got {type(writer)}"
            )
        self.writer = writer

    def __call__(self, key, *args, **kwargs):
        self.writer.put(key, *args, **kwargs)


class ImageCSVInput(BaseInput):
    def __init__(self, csv_path, colnames=[], id_column=None, readers=[read_image]):
        loader = ImageCSVLoader(csv_path, colnames, id_column, readers)
        super().__init__(loader)


class ImageFileInput(BaseInput):
    def __init__(self,
                 root_directory,
                 get_subject_id_from="filename",
                 subdir_path=None,
                 exclude_paths=[],
                 reader=read_image):
        loader = ImageFileLoader(root_directory,
                                 get_subject_id_from,
                                 subdir_path,
                                 exclude_paths,
                                 reader)
        super().__init__(loader)


class ImageFileOutput(BaseOutput):
    def __init__(self,
                 root_directory,
                 filename_format="{subject_id}.nrrd",
                 create_dirs=True,
                 compress=True):
        writer = ImageFileWriter(root_directory,
                                 filename_format,
                                 create_dirs,
                                 compress)
        super().__init__(writer)


class NumpyOutput(BaseOutput):
    def __init__(self,
                 root_directory,
                 filename_format="{subject_id}.npy",
                 create_dirs=True):
        writer = NumpyWriter(root_directory, filename_format, create_dirs)
        super().__init__(writer)


class HDF5Output(BaseOutput):
    def __init__(self,
                 root_directory,
                 filename_format="{subject_id}.h5",
                 create_dirs=True,
                 save_geometry=True):
        writer = HDF5Writer(root_directory,
                            filename_format,
                            create_dirs,
                            save_geometry)
        super().__init__(writer)


class MetadataOutput(BaseOutput):
    def __init__(self,
                 root_directory,
                 filename_format="{subject_id}.json",
                 create_dirs=True):
        writer = MetadataWriter(root_directory, filename_format, create_dirs)
        super().__init__(writer)


# Resampling ops

class Resample(BaseOp):
    def __init__(self,
                 spacing,
                 interpolation="linear",
                 anti_alias=True,
                 anti_alias_sigma=None,
                 transform=None,
                 output_size=None):
        self.spacing = spacing
        self.interpolation = interpolation
        self.anti_alias = anti_alias
        self.anti_alias_sigma = anti_alias_sigma
        self.transform = transform
        self.output_size = output_size

    def __call__(self, image):
        return resample(image,
                        spacing=self.spacing,
                        interpolation=self.interpolation,
                        anti_alias=self.anti_alias,
                        anti_alias_sigma=self.anti_alias_sigma,
                        transform=self.transform,
                        output_size=self.output_size)


class Resize(BaseOp):
    def __init__(self,
                 size,
                 interpolation="linear",
                 anti_alias=True,
                 anti_alias_sigma=None):
        self.size = size
        self.interpolation = interpolation
        self.anti_alias = anti_alias
        self.anti_alias_sigma = anti_alias_sigma

    def __call__(self, image):
        return resize(image,
                      new_size=self.size,
                      interpolation=self.interpolation,
                      anti_alias_sigma=anti_alias_sigma)

class Zoom(BaseOp):
    def __init__(self,
                 scale_factor,
                 interpolation="linear",
                 anti_alias=True,
                 anti_alias_sigma=None):
        self.scale_factor = scale_factor
        self.interpolation = interpolation
        self.anti_alias = anti_alias
        self.anti_alias_sigma = anti_alias_sigma

    def __call__(self, image):
        return zoom(image,
                    self.scale_factor,
                    interpolation=self.interpolation,
                    anti_alias=self.anti_alias,
                    anti_alias_sigma=self.anti_alias_sigma)


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


# Cropping & mask ops

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
                        world_coordinates=self.world_coordinates)


class CropToMaskBoundingBox(BaseOp):
    def __init__(self, margin):
        self.margin = margin

    def __call__(self, image, mask=None, label=1):
        return crop_to_mask_bounding_box(image,
                                         mask,
                                         margin=self.margin,
                                         label=label)

# Intensity ops

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


# Lambda ops

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


# Segmentation ops

class StructureSetToSegmentation(BaseOp):
    def __init__(self, roi_names):
        self.roi_names = roi_names

    def __call__(self, structure_set, reference_image):
        return structure_set.to_segmentation(reference_image, roi_names=self.roi_names)

class MapOverLabels(BaseOp):
    def __init__(self, op, include_background=False, return_segmentation=True):
        self.op = op
        self.include_background = include_background
        self.return_seg = return_seg

    def __call__(self, segmentation, **kwargs):
        return map_over_labels(segmentation,
                               self.op,
                               include_background=self.include_background,
                               return_segmentation=self.return_segmentation,
                               **kwargs)



