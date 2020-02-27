import numpy as np
import SimpleITK as sitk

from .functional import *


class BaseOp:
    def __call__(self, *args, **kwargs):
        raise NotImplementedError


class Resample(BaseOp):
    def __init__(self, spacing, interpolation="linear", anti_alias=True, anti_alias_sigma=2., transform=None):
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
        return resize(image, new_size=self.size, interpolation=self.interpolation)

class Rotate(BaseOp):
    def __init__(self, rotation_centre, angles, interpolation="linear"):
        self.rotation_centre = rotation_centre
        self.angles = angles
        self.interpolation = interpolation

    def __call__(self, image):
        return rotate(image, rotation_centre=self.rotation_centre, angles=self.angles, interpolation=self.interpolation)


class InPlaneRotate(BaseOp):
    def __init__(self, angle, interpolation="linear"):
        self.angle = angle
        self.interpolation = interpolation

    def __call__(self, image):
        image_size = np.array(image.GetSize())
        image_centre = image_size // 2
        angles = (0., 0., self.angle)
        return rotate(image, rotation_centre=image_centre, angles=angles, interpolation=self.interpolation)

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


# def constant_pad(image, size, cval=0.):
#     pass

# def centre_on_point(image, centre):
#     pass


# def clip(image, lower, upper):
#     pass


# def window(image, window, level):
#     pass


# def mean(image, mask=None, labels=None):
#     if mask is not None:
#         pass
#     pass

# def var(image, mask=None, labels=None):
#     if mask is not None:
#         pass
#     pass

# def standard_scale(image, dataset_mean=0., dataset_var=1.):
#     return (image - dataset_mean) / dataset_var
