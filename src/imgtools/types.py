from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Iterator, NamedTuple, Sequence, TypeVar, Union

import numpy as np
import SimpleITK as sitk

IntOrFloat = TypeVar("T", int, float)


class ImageGeometry(NamedTuple):
    """
    Represent the geometry of a 3D image, including its size, origin, direction,
    and spacing.
    """

    size: Size3D
    origin: Coordinate
    direction: Sequence[float]
    spacing: Spacing3D


@dataclass
class Vector3D(Generic[IntOrFloat]):
    """Base class for a 3D vector representation."""

    x: IntOrFloat
    y: IntOrFloat
    z: IntOrFloat

    def __post_init__(self):
        for dim, name in zip(self.as_tuple, ["x", "y", "z"]):
            self._validate_dimension(dim, name)

    @property
    def as_tuple(self) -> tuple[IntOrFloat, IntOrFloat, IntOrFloat]:
        return self.x, self.y, self.z

    def _validate_dimension(self, dim: IntOrFloat, name: str) -> None:
        """Validation method to be overridden by subclasses."""
        pass

    def __add__(self, other: Vector3D[IntOrFloat]) -> Vector3D[IntOrFloat]:
        return self.__class__(x=self.x + other.x, y=self.y + other.y, z=self.z + other.z)

    def __sub__(self, other: Vector3D[IntOrFloat]) -> Vector3D[IntOrFloat]:
        return self.__class__(x=self.x - other.x, y=self.y - other.y, z=self.z - other.z)


@dataclass
class Spacing3D(Vector3D[float]):
    """Represent the spacing of a 3D object with float constraints."""

    def _validate_dimension(self, dim: float, name: str) -> None:
        match dim:
            case float():
                pass
            case _:
                raise TypeError(
                    f"{name} must be a number (float or int), got {dim} ({self.as_tuple=})"
                )
        if dim <= 0:
            raise ValueError(f"{name} must be positive, got {dim}")

    def __repr__(self) -> str:
        """Round the spacing values to 3 decimal places."""
        return f"Spacing3D(x={self.x:.3f}, y={self.y:.3f}, z={self.z:.3f})"


@dataclass
class Point3D(Vector3D[int]):
    """Represent a point in 3D space with integer constraints."""

    def _validate_dimension(self, dim: int, name: str) -> None:
        match dim:
            case int():
                pass
            case float() if dim.is_integer():
                pass
            case _:
                raise TypeError(f"{name} must be a whole number, got {dim} ({self.as_tuple=})")

        # Ensure the value is stored as an integer
        setattr(self, name, int(dim))


@dataclass
class Size3D(Point3D):
    """Represent the size of a 3D object with positive integer constraints."""

    def _validate_dimension(self, dim: int, name: str) -> None:
        super()._validate_dimension(dim, name)
        if dim < 0:
            raise ValueError(f"{name} must be positive or 0, got {dim}")

    @property
    def volume(self) -> int:
        return self.x * self.y * self.z

    @classmethod
    def from_tuple(cls, size: tuple[int, int, int]) -> Size3D:
        return cls(*size)


@dataclass
class Coordinate(Point3D):
    """Represent a coordinate in 3D space."""

    pass


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
                raise ValueError("If image is a Numpy array, either geometry must be specified.")

            if geometry is not None:
                _, origin, direction, spacing = geometry

            self._image = sitk.GetImageFromArray(image)
            self._image.SetOrigin(origin[::-1])
            direction = tuple(direction)
            self._image.SetDirection(direction[:-3] + direction[3:6] + direction[:3])
            self._image.SetSpacing(spacing[::-1])
        else:
            msg = f"image must be either numpy.ndarray or SimpleITK.Image, not {type(image)}."
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
        other_val = getattr(other, "_image", other)
        return Image(self._image + other_val)

    def __sub__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, "_image", other)
        return Image(self._image - other_val)

    def __mul__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, "_image", other)
        return Image(self._image * other_val)

    def __div__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, "_image", other)
        return Image(self._image / other_val)

    def __floordiv__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, "_image", other)
        return Image(self._image // other_val)

    def __pow__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, "_image", other)
        return Image(self._image**other_val)

    def __iadd__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, "_image", other)
        self._image += other_val

    def __isub__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, "_image", other)
        self._image -= other_val

    def __imul__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, "_image", other)
        self._image *= other_val

    def __idiv__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, "_image", other)
        self._image /= other_val

    def __ifloordiv__(self, other: Union[Image, Image]) -> Image:
        other_val = getattr(other, "_image", other)
        self._image //= other_val

    def __iter__(self) -> Iterator:
        pass

    def __repr__(self) -> str:
        return (
            f"Image(image={self._image}, origin={self.origin}, "
            f"spacing={self.spacing}, direction={self.direction})"
        )

    def __str__(self) -> str:
        return (
            f"origin = {self.origin}\n"
            f"spacing = {self.spacing}\n"
            f"direction = {self.direction}\n"
            f"values = \n{self.to_numpy(view=True)}"
        )
