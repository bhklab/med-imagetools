from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Type

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
    """A class for handling medical images with geometric properties.

    Extends SimpleITK.Image with additional properties and methods for
    medical image processing and analysis.
    """

    @property
    def size(self) -> Size3D:
        """Get the size of the image in voxels.

        Returns
        -------
        Size3D
            The dimensions of the image (width, height, depth).
        """
        return Size3D(*self.GetSize())

    @property
    def origin(self) -> Coordinate3D:
        """Get the physical coordinates of the first voxel.

        Returns
        -------
        Coordinate3D
            The physical coordinates (x, y, z) of the origin.
        """
        return Coordinate3D(*self.GetOrigin())

    @property
    def spacing(self) -> Spacing3D:
        """Get the physical size of each voxel.

        Returns
        -------
        Spacing3D
            The spacing between voxels in physical units.
        """
        return Spacing3D(*self.GetSpacing())

    @property
    def direction(self) -> Direction:
        """Get the direction cosine matrix for image orientation.

        Returns
        -------
        Direction
            The 3x3 direction matrix representing image orientation.
        """
        return Direction(tuple(self.GetDirection()))

    @property
    def geometry(self) -> ImageGeometry:
        """Get a complete representation of the image geometry.

        Returns
        -------
        ImageGeometry
            A dataclass containing size, origin, direction, and spacing.
        """
        return ImageGeometry(
            size=self.size,
            origin=self.origin,
            direction=self.direction,
            spacing=self.spacing,
        )

    @property
    def ndim(self) -> int:
        """Get the number of dimensions of the image.

        Returns
        -------
        int
            The dimensionality of the image (typically 3 for medical images).
        """
        return self.GetDimension()

    @property
    def dtype_np(self) -> Type["np.number"]:
        """Get the NumPy data type corresponding to the image's pixel type.

        Returns
        -------
        Type[np.number]
            The NumPy data type of the image pixels.
        """
        return sitk.extra._get_numpy_dtype(self)

    @property
    def dtype_str(self) -> str:
        return self.GetPixelIDTypeAsString()

    @property
    def img_stats(self) -> dict[str, Any]:  # noqa: ANN001
        """Get image statistics."""
        img_stats = {
            "dtype": self.dtype_str,
            "dtype_numpy": self.dtype_np,
            "size": self.size,
            "spacing": self.spacing,
            "origin": self.origin,
            "direction": self.direction,
        }
        return img_stats

    def __rich_repr__(self):  # type: ignore[no-untyped-def] # noqa: ANN204
        yield "ndim", self.ndim
        yield "dtype_numpy", self.dtype_np
        yield "dtype", self.dtype_str
        yield "size", self.size
        yield "origin", self.origin
        yield "spacing", self.spacing
        yield "direction", self.direction

    def to_numpy(
        self, view: bool = False
    ) -> np.ndarray | tuple[np.ndarray, ImageGeometry]:
        """Convert the image to a NumPy array.

        Parameters
        ----------
        view : bool, optional
            Whether to return a view instead of a copy of the array, by default False.
            Using a view can save memory but modifications to the array may affect the original image.

        Returns
        -------
        tuple[np.ndarray, ImageGeometry]
            A tuple containing the NumPy array and the image geometry.

        Notes
        -----
        The returned NumPy array has axes ordered as (z, y, x), which is different
        from the SimpleITK convention of (x, y, z).
        """
        if view:
            array = sitk.GetArrayViewFromImage(self)
        else:
            array = sitk.GetArrayFromImage(self)
        return array, self.geometry


if __name__ == "__main__":
    from rich import print  # noqa: A004

    from imgtools.datasets import example_data

    img = example_data()["duck"]
    as_medimage = MedImage(img)
    print(as_medimage)
