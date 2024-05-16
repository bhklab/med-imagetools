import SimpleITK as sitk
import numpy as np

from typing import NamedTuple, Sequence, Union

# ImageGeometry = namedtuple("ImageGeometry", "origin, direction, spacing")

class ImageGeometry(NamedTuple):
    size:      Sequence[int]
    origin:    Sequence[float]
    direction: Sequence[float]
    spacing:   Sequence[float]


def physical_point_to_index(point, reference_geometry, continuous=False):
    if isinstance(reference_geometry, ImageGeometry):
        ref_image = sitk.Image(reference_geometry.size[::-1], 0)
        ref_image.SetOrigin(reference_geometry.origin[::-1])
        direction = reference_geometry.direction
        direction_rev = direction[:-3] + direction[3:6] + direction[:3]
        ref_image.SetDirection(direction_rev)
        ref_image.SetSpacing(reference_geometry.spacing[::-1])
    elif isinstance(reference_geometry, Image):
        ref_image = reference_geometry._image
    elif isinstance(reference_geometry, sitk.Image):
        ref_image = reference_geometry
    else:
        raise ValueError(f"Reference geometry must be of type `ImageGeometry`, `imgtools.Image` or `sitk.Image`, got {type(reference_geometry)}")

    if continuous:
        return ref_image.TransformPhysicalPointToContinuousIndex(point[::-1])[::-1]
    else:
        return ref_image.TransformPhysicalPointToIndex(point[::-1])[::-1]


def index_to_physical_point(index, reference_geometry):
    if isinstance(reference_geometry, ImageGeometry):
        ref_image = sitk.Image(reference_geometry.size[::-1], 0)
        ref_image.SetOrigin(reference_geometry.origin[::-1])
        direction = reference_geometry.direction
        direction_rev = direction[:-3] + direction[3:6] + direction[:3]
        ref_image.SetDirection(direction_rev)
        ref_image.SetSpacing(reference_geometry.spacing[::-1])
    elif isinstance(reference_geometry, Image):
        ref_image = reference_geometry._image
    elif isinstance(reference_geometry, sitk.Image):
        ref_image = reference_geometry
    else:
        raise ValueError(f"Reference geometry must be of type ImageGeometry, imgtools.Image or sitk.Image, got {type(reference_geometry)}")

    continuous = any([isinstance(i, float) for i in index])

    if continuous:
        return ref_image.TransformContinuousIndexToPhysicalPoint(index[::-1])[::-1]
    else:
        return ref_image.TransformIndexToPhysicalPoint(index[::-1])[::-1]


# Goals for this module:
# - One Image Class to Rule Them All (no more juggling numpy & sitk)
# - consistent indexing (z, y, x) (maybe fancy indexing?)
# - can be created either from array or sitk.Image
# - implements all basic operators of sitk.Image
# - easy conversion to array or sitk
# - method to apply arbitrary sitk filter
# - nicer repr

# TODO:
# - better support for masks (e.g. what happens when we pass a one-hot encoded mask?)
# - (optional) specify indexing order when creating new Image (sitk or numpy)


class Image:
    def __init__(self,
                 image:     Union[sitk.Image, np.ndarray] = None,
                 geometry:  ImageGeometry   = None,
                 origin:    Sequence[float] = None,
                 direction: Sequence[float] = None,
                 spacing:   Sequence[float] = None):

        if isinstance(image, sitk.Image):
            self._image = image
        elif isinstance(image, np.ndarray):
            if geometry is None and any((origin is None, direction is None, spacing is None)):
                raise ValueError(
                    "If image is a Numpy array, either geometry must be specified."
                )

            if geometry is not None:
                _, origin, direction, spacing = geometry

            self._image = sitk.GetImageFromArray(image)
            self._image.SetOrigin(origin[::-1])
            direction = tuple(direction)
            self._image.SetDirection(direction[:-3] + direction[3:6] + direction[:3])
            self._image.SetSpacing(spacing[::-1])
        else:
            raise TypeError(
                f"image must be either numpy.ndarray or SimpleITK.Image, not {type(image)}."
            )

    @property
    def size(self):
        return self._image.GetSize()[::-1]

    @property
    def origin(self):
        return self._image.GetOrigin()[::-1]

    @property
    def direction(self):
        direction = self._image.GetDirection()
        direction = direction[:-3] + direction[3:6] + direction[:3]
        return direction

    @property
    def spacing(self):
        return self._image.GetSpacing()[::-1]

    @property
    def geometry(self):
        return ImageGeometry(size=self.size,
                             origin=self.origin,
                             direction=self.direction,
                             spacing=self.spacing)

    @property
    def size(self):
        return self._image.GetSize()[::-1]

    @property
    def ndim(self):
        return len(self.size)

    @property
    def dtype(self):
        return self._image.GetPixelIDType()

    def astype(self, new_type):
        return Image(sitk.Cast(self._image, new_type))

    def to_sitk_image(self):
        return self._image

    def to_numpy(self, return_geometry=False, view=False):
        if view:
            array = sitk.GetArrayViewFromImage(self._image)
        else:
            array = sitk.GetArrayFromImage(self._image)
        if return_geometry:
            return array, self.geometry
        return array

    def __getitem__(self, idx):
        if isinstance(idx, (int, slice)):
            idx = (idx, )
        if len(idx) < self.ndim:
            idx += (slice(None), ) * (self.ndim - len(idx))

        idx = idx[::-1]  # SimpleITK uses (x, y, z) ordering internally

        value = self._image[idx]

        try:  # XXX there probably is a nicer way to check if value is a scalar
            return Image(value)
        except TypeError:
            return value

    def __setitem__(self, idx, value):
        if isinstance(idx, (int, slice)):
            idx = (idx, )
        if len(idx) < self.ndim:
            idx += (slice(None), ) * (self.ndim - len(idx))

        idx = idx[::-1]  # SimpleITK uses (x, y, z) ordering internally

        value = self._image[idx]

        try:  # XXX there probably is a nicer way to check if value is a scalar
            return Image(value)
        except TypeError:
            return value

    def apply_filter(self, sitk_filter):
        result = sitk_filter.Execute(self._image)
        if isinstance(result, sitk.Image):
            return Image(result)
        else:
            return result

    def __neg__(self):
        return Image(-self._image)

    def __abs__(self):
        return Image(abs(self._image))

    def __invert__(self):
        return Image(~self._image)

    def __add__(self, other):
        other_val = getattr(other, "_image", other)
        return Image(self._image + other_val)

    def __sub__(self, other):
        other_val = getattr(other, "_image", other)
        return Image(self._image - other_val)

    def __mul__(self, other):
        other_val = getattr(other, "_image", other)
        return Image(self._image * other_val)

    def __div__(self, other):
        other_val = getattr(other, "_image", other)
        return Image(self._image / other_val)

    def __floordiv__(self, other):
        other_val = getattr(other, "_image", other)
        return Image(self._image / other_val)

    def __pow__(self, other):
        other_val = getattr(other, "_image", other)
        return Image(self._image ** other_val)

    def __iadd__(self, other):
        other_val = getattr(other, "_image", other)
        self._image += other_val

    def __isub__(self, other):
        other_val = getattr(other, "_image", other)
        self._image -= other_val

    def __imul__(self, other):
        other_val = getattr(other, "_image", other)
        self._image *= other_val

    def __idiv__(self, other):
        other_val = getattr(other, "_image", other)
        self._image /= other_val

    def __ifloordiv__(self, other):
        other_val = getattr(other, "_image", other)
        self._image //= other_val

    def __iter__(self):
        pass

    def __repr__(self):
        return f"Image(image={self._image}, origin={self.origin}, spacing={self.spacing}, direction={self.direction})"

    def __str__(self):
        return f"origin = {self.origin}\nspacing = {self.spacing}\ndirection = {self.direction}\nvalues = \n{self.to_numpy(view=True)}"
