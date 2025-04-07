from __future__ import annotations

from dataclasses import dataclass
from typing import Type

import numpy as np
import SimpleITK as sitk

from imgtools.coretypes.direction import Direction
from imgtools.coretypes.spatial_types import (
    Coordinate3D,
    Size3D,
    Spacing3D,
)


@dataclass(frozen=True)
class ImageGeometry:
    """Represents the geometry of a 3D image."""

    size: Size3D
    origin: Coordinate3D
    direction: Direction
    spacing: Spacing3D


# Type alias for Image or Array
ImageOrArray = sitk.Image | np.ndarray


class MedImage(sitk.Image):
    @property
    def size(self) -> Size3D:
        return Size3D(*self.GetSize())

    @property
    def origin(self) -> Coordinate3D:
        return Coordinate3D(*self.GetOrigin())

    @property
    def spacing(self) -> Spacing3D:
        return Spacing3D(*self.GetSpacing())

    @property
    def direction(self) -> Direction:
        return Direction(tuple(self.GetDirection()))

    @property
    def geometry(self) -> ImageGeometry:
        return ImageGeometry(
            size=self.size,
            origin=self.origin,
            direction=self.direction,
            spacing=self.spacing,
        )

    @property
    def ndim(self) -> int:
        return self.GetDimension()

    @property
    def dtype_np(self) -> Type["np.number"]:
        return sitk.extra._get_numpy_dtype(self)

    @property
    def dtype_str(self) -> str:
        return self.GetPixelIDTypeAsString()

    def __rich_repr__(self):  # noqa: ANN204
        yield "ndim", self.ndim
        yield "dtype_numpy", self.dtype_np
        yield "dtype", self.dtype_str
        yield "size", self.size
        yield "origin", self.origin
        yield "spacing", self.spacing
        yield "direction", self.direction

    def to_numpy(
        self, return_geometry: bool = False, view: bool = False
    ) -> np.ndarray | tuple[np.ndarray, ImageGeometry]:
        if view:
            array = sitk.GetArrayViewFromImage(self)
        else:
            array = sitk.GetArrayFromImage(self)
        if return_geometry:
            return array, self.geometry
        return array


if __name__ == "__main__":
    from rich import print  # noqa: A004

    from imgtools.datasets import example_data

    img = example_data()["duck"]
    as_medimage = MedImage(img)
    print(as_medimage)
