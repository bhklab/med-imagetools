from __future__ import annotations

from typing import TYPE_CHECKING, Any, Type

import SimpleITK as sitk

from imgtools.coretypes.spatial_types import (
    Coordinate3D,
    Direction,
    ImageGeometry,
    Size3D,
    Spacing3D,
)

if TYPE_CHECKING:
    from pathlib import Path

    import numpy as np


class MedImage(sitk.Image):
    """A more convenient wrapper around SimpleITK.Image.

    Extends SimpleITK.Image with additional properties and methods for
    medical image processing and analysis.
    """

    metadata: dict[str, Any]

    @classmethod
    def from_file(
        cls, filepath: str | "Path", metadata: dict[str, Any] | None = None
    ) -> "MedImage":
        """Create a MedImage from a file path with optional metadata.

        This method filters out any fingerprint-related keys from the provided metadata.

        Parameters
        ----------
        filepath : str | Path
            Path to the image file
        metadata : dict[str, Any] | None, optional
            Optional metadata dictionary, by default None

        Returns
        -------
        MedImage
            A new MedImage instance

        Notes
        -----
        The following fingerprint-related keys will be filtered out from metadata:
        - class, hash, size, ndim, nvoxels, spacing, origin, direction
        - min, max, sum, mean, std, variance
        - dtype_str, dtype_numpy
        """
        # Load the image file
        image = sitk.ReadImage(filepath)

        # Create instance of the class (MedImage or a subclass)
        instance = cls(image)

        if not metadata:
            return instance

        # Process metadata if provided
        # Define fingerprint keys to filter out
        fingerprint_keys = {
            "class", "hash", "size", "ndim", "nvoxels", "spacing", 
            "origin", "direction", "min", "max", "sum", "mean", "std", 
            "variance", "dtype_str", "dtype_numpy"
        }  # fmt: skip
        # Filter metadata to exclude fingerprint keys
        instance.metadata = {
            k: v for k, v in metadata.items() if k not in fingerprint_keys
        }
        return instance

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
        """Wrapper around GetDimension."""
        return self.GetDimension()

    @property
    def dtype(self) -> int:
        """Wrapper around GetPixelID."""
        return self.GetPixelID()

    @property
    def dtype_str(self) -> str:
        """Wrapper around GetPixelIDTypeAsString."""
        return self.GetPixelIDTypeAsString()

    @property
    def dtype_np(self) -> Type["np.number"]:
        """Get the NumPy data type corresponding to the image's pixel type."""
        return sitk.extra._get_numpy_dtype(self)

    @property
    def fingerprint(self) -> dict[str, Any]:  # noqa: ANN001
        """Get image statistics."""
        filter_ = sitk.StatisticsImageFilter()
        filter_.Execute(self)
        return {
            "class": self.__class__.__name__,
            "hash": sitk.Hash(self),
            "size": self.size,
            "ndim": self.ndim,
            "nvoxels": self.size.volume,
            "spacing": self.spacing,
            "origin": self.origin,
            "direction": self.direction,
            "min": filter_.GetMinimum(),
            "max": filter_.GetMaximum(),
            "sum": filter_.GetSum(),
            "mean": filter_.GetMean(),
            "std": filter_.GetSigma(),
            "variance": filter_.GetVariance(),
            "dtype_str": self.dtype_str,
            "dtype_numpy": self.dtype_np,
        }

    @property
    def serialized_fingerprint(self) -> dict[str, Any]:
        """Get a serialized version of the image fingerprint with primitive types.

        Returns
        -------
        dict[str, Any]
            A dictionary with serialized image metadata that can be easily
            converted to JSON or other serialization formats.
        """
        fp = self.fingerprint.copy()
        # Convert custom types to tuples
        for k, v in fp.items():
            if isinstance(v, (Coordinate3D, Size3D, Spacing3D)):
                fp[k] = v.to_tuple()
            elif isinstance(v, Direction):
                fp[k] = v.matrix
        return fp

    def __rich_repr__(self):  # type: ignore[no-untyped-def] # noqa: ANN204
        yield "ndim", self.ndim
        yield "dtype_str", self.dtype_str
        yield "dtype_numpy", self.dtype_np
        yield "size", self.size
        yield "origin", self.origin
        yield "spacing", self.spacing
        yield "direction", self.direction

    def to_numpy(self, view: bool = False) -> tuple[np.ndarray, ImageGeometry]:
        """Convert the image to a NumPy array.

        Parameters
        ----------
        view : bool, optional
            Whether to return a view instead of a copy of the array, by default False.
            Views are more memory efficient but dont allow for modification of the array.

        Returns
        -------
        tuple[np.ndarray, ImageGeometry]
            A tuple containing the NumPy array and the image geometry with
            size, origin, direction, and spacing.

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
