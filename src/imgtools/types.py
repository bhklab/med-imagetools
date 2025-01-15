from __future__ import annotations

from typing import Any, Iterator, NamedTuple, Sequence, Union

import numpy as np
import SimpleITK as sitk


class ImageGeometry(NamedTuple):
    size: Sequence[int]
    origin: Sequence[float]
    direction: Sequence[float]
    spacing: Sequence[float]


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

# Type alias for Image or Array
ImageOrArray = Union[sitk.Image, np.ndarray]


class Image:
    def __init__(
        self,
        image: ImageOrArray,
        geometry: ImageGeometry | None = None,
        origin: Sequence[float] | None = None,
        direction: Sequence[float] | None = None,
        spacing: Sequence[float] | None = None,
    ) -> None:
        if isinstance(image, sitk.Image):
            self._image = image
        elif isinstance(image, np.ndarray):
            if geometry is None and any((origin is None, direction is None, spacing is None)):
                raise ValueError('If image is a Numpy array, either geometry must be specified.')

            if geometry is not None:
                _, origin, direction, spacing = geometry

            self._image = sitk.GetImageFromArray(image)
            self._image.SetOrigin(origin[::-1])
            direction = tuple(direction)
            self._image.SetDirection(direction[:-3] + direction[3:6] + direction[:3])
            self._image.SetSpacing(spacing[::-1])
        else:
            msg = f'image must be either numpy.ndarray or SimpleITK.Image, not {type(image)}.'
            raise TypeError(msg)

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
        return ImageGeometry(
            size=self.size,
            origin=self.origin,
            direction=self.direction,
            spacing=self.spacing,
        )

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

    def to_numpy(
        self, return_geometry: bool = False, view: bool = False
    ) -> Union[np.ndarray, tuple[np.ndarray, ImageGeometry]]:
        if view:
            array = sitk.GetArrayViewFromImage(self._image)
        else:
            array = sitk.GetArrayFromImage(self._image)
        if return_geometry:
            return array, self.geometry
        return array

    def __getitem__(self, idx: int | slice) -> Union[Image, Any]:  # noqa
        if isinstance(idx, (int, slice)):
            idx = (idx,)
        if len(idx) < self.ndim:
            idx += (slice(None),) * (self.ndim - len(idx))

        idx = idx[::-1]  # SimpleITK uses (x, y, z) ordering internally

        value = self._image[idx]

        try:  # XXX there probably is a nicer way to check if value is a scalar
            return Image(value)
        except TypeError:
            return value

    def __setitem__(self, idx: int | slice, value: Any) -> None:  # noqa
        if isinstance(idx, (int, slice)):
            idx = (idx,)
        if len(idx) < self.ndim:
            idx += (slice(None),) * (self.ndim - len(idx))

        idx = idx[::-1]  # SimpleITK uses (x, y, z) ordering internally

        value = self._image[idx]

        try:  # XXX there probably is a nicer way to check if value is a scalar
            return Image(value)
        except TypeError:
            return value

    def apply_filter(self, sitk_filter: sitk.ImageFilter) -> Union[Image, Any]:  # noqa
        result = sitk_filter.Execute(self._image)
        if isinstance(result, sitk.Image):
            return Image(result)
        else:
            return result

    def __neg__(self) -> Image:
        return Image(-self._image)

    def __abs__(self) -> Image:
        return Image(abs(self._image))

    def __invert__(self) -> Image:
        return Image(~self._image)

    def __add__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, '_image', other)
        return Image(self._image + other_val)

    def __sub__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, '_image', other)
        return Image(self._image - other_val)

    def __mul__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, '_image', other)
        return Image(self._image * other_val)

    def __div__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, '_image', other)
        return Image(self._image / other_val)

    def __floordiv__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, '_image', other)
        return Image(self._image // other_val)

    def __pow__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, '_image', other)
        return Image(self._image**other_val)

    def __iadd__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, '_image', other)
        self._image += other_val

    def __isub__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, '_image', other)
        self._image -= other_val

    def __imul__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, '_image', other)
        self._image *= other_val

    def __idiv__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, '_image', other)
        self._image /= other_val

    def __ifloordiv__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, '_image', other)
        self._image //= other_val

    def __iter__(self) -> Iterator:
        pass

    def __repr__(self) -> str:
        return (
            f'Image(image={self._image}, origin={self.origin}, '
            f'spacing={self.spacing}, direction={self.direction})'
        )

    def __str__(self) -> str:
        return (
            f'origin = {self.origin}\n'
            f'spacing = {self.spacing}\n'
            f'direction = {self.direction}\n'
            f'values = \n{self.to_numpy(view=True)}'
        )
