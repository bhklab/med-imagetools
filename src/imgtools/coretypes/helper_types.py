"""
helper_types.py: Intuitive and reusable types for 3D spatial operations.

This module defines foundational types to represent and manipulate 3D spatial
concepts intuitively, focusing on clarity, usability, and alignment with
medical imaging workflows. These types aim to simplify operations like
spatial transformations, bounding box calculations, and metadata representation.

## Goals:
- **Intuitive Design:** Variable names and methods should be easy to understand
  and reflect their real-world meaning.
- **Reusability:** Types should be generic enough to apply to various spatial
  operations across domains, especially medical imaging.
- **Consistency:** Ensure compatibility with spatial metadata in imaging formats
  (e.g., DICOM, NIfTI).
- **Extendability:** Enable seamless addition of new spatial concepts as needed.

## Types:
1. **Point3D**
   - Represents a point in 3D space with x, y, z coordinates.
   - Includes methods for basic vector arithmetic (addition, subtraction).

2. **Size3D**
   - Represents the dimensions of a 3D object (width, height, depth).
   - Derived from `Point3D` but semantically indicates size rather than position.

3. **Coordinate**
   - Represents a specific coordinate in 3D space.
   - Identical in structure to `Point3D` but used to denote spatial locations.

4. **Direction**
   - Represents a directional vector in 3D space, useful for orientation.
   - Includes normalization and utility functions to ensure consistency with
     medical imaging metadata like direction cosines.

These types serve as building blocks for higher-level spatial operations and
enhance code readability, ensuring that spatial concepts are represented
accurately and intuitively.

Examples:
---------
>>> point = Point3D(x=10, y=20, z=30)
>>> size = Size3D(x=50, y=60, z=70)
>>> coord = Coordinate(x=5, y=5, z=5)
>>> direction =
"""

from __future__ import annotations

import numpy as np
import SimpleITK as sitk
from dataclasses import dataclass

from typing import NamedTuple, Sequence
from typing import Tuple, Iterator, TypeAlias
import numpy as np

Matrix3D: TypeAlias = Tuple[
    Tuple[float, float, float],
    Tuple[float, float, float],
    Tuple[float, float, float],
]
Matrix3DFlat: TypeAlias = Tuple[
    float, float, float, float, float, float, float, float, float
]

FlattenedMatrix = Matrix3DFlat


# @dataclass(frozen=True)
# class ImageGeometry:
#     """Represents the geometry of a 3D image."""

#     size: Size3D
#     origin: Point3D
#     direction: Direction
#     spacing: Spacing


@dataclass
class Vector3D:
    """
    Represent a vector in 3D space.

    Attributes
    ----------
    x : float
        X-component of the vector.
    y : float
        Y-component of the vector.
    z : float
        Z-component of the vector.

    Methods
    -------
    __add__(other):
        Add another Vector3D to this vector.
    __sub__(other):
        Subtract another Vector3D from this vector.
    __iter__():
        Iterate over the components (x, y, z).
    """

    x: float
    y: float
    z: float

    def __init__(self, *args: float) -> None:
        """Initialize a Vector3D with x, y, z components."""
        match args:
            case [x, y, z]:
                self.x, self.y, self.z = x, y, z
            case [tuple_points] if isinstance(tuple_points, tuple):
                self.x, self.y, self.z = tuple_points
            case _:
                errmsg = (
                    f"{self.__class__.__name__} expects 3 values for x, y, z."
                    f" Got {len(args)} values for {args}."
                )
                raise ValueError(errmsg)

    def __iter__(self) -> Iterator[float]:
        """Allow iteration over the components."""
        return iter((self.x, self.y, self.z))

    def __repr__(self) -> str:
        """Return a string representation of the Vector3D."""
        cls = self.__class__.__name__
        return f"{cls}(x={self.x:.1f}, y={self.y:.1f}, z={self.z:.1f})"


class Spacing(Vector3D):
    """
    Represent the spacing in 3D space.
    Inherits from Vector3D.
    """

    # No exta attributes or methods needed (yet),
    # inherits everything from Vector3D


class Coordinate3D(Vector3D):
    """
    Represent a point in 3D space.
    Inherits from Vector3D.

    Can add and subtract other Point3D or Size3D objects.
    """

    def __add__(self, other: Coordinate3D | Size3D) -> Coordinate3D:
        """Add another Vector3D to this vector."""
        match other:
            case Coordinate3D(x, y, z):
                return Coordinate3D(self.x + x, self.y + y, self.z + z)
            case Size3D(width, height, depth):
                return Coordinate3D(
                    self.x + width, self.y + height, self.z + depth
                )
            case tuple() if len(other) == 3:
                return Coordinate3D(
                    self.x + other[0], self.y + other[1], self.z + other[2]
                )
            case _:
                errmsg = (
                    f"Unsupported type for addition: {type(other)}."
                    " Expected Coordinate3D or Size3D."
                )

    def __sub__(self, other: Coordinate3D | Size3D) -> Coordinate3D:
        """Subtract another Vector3D from this vector."""
        match other:
            case Coordinate3D(x, y, z):
                return Coordinate3D(self.x - x, self.y - y, self.z - z)
            case Size3D(width, height, depth):
                return Coordinate3D(
                    self.x - width, self.y - height, self.z - depth
                )
            case tuple() if len(other) == 3:
                return Coordinate3D(
                    self.x - other[0], self.y - other[1], self.z - other[2]
                )
            case _:
                errmsg = (
                    f"Unsupported type for subtraction: {type(other)}."
                    " Expected Point3D or Size3D."
                )
                raise TypeError(errmsg)


@dataclass
class Size3D:
    """
    Represent the size (width, height, depth) of a 3D object.

    Attributes
    ----------
    width : float
        The width of the 3D object.
    height : float
        The height of the 3D object.
    depth : float
        The depth of the 3D object.

    Methods
    -------
    volume:
        Calculate the volume of the 3D object.
    """

    width: float
    height: float
    depth: float

    def __init__(self, *args: float) -> None:
        match args:
            case [width, height, depth]:
                self.width, self.height, self.depth = width, height, depth
            case [tuple_points] if isinstance(tuple_points, tuple):
                self.width, self.height, self.depth = tuple_points
            case _:
                errmsg = (
                    f"{self.__class__.__name__} expects 3 values for width, height, depth."
                    f" Got {len(args)} values for {args}."
                )

    @property
    def volume(self) -> float:
        """Calculate the volume of the 3D object."""
        return self.width * self.height * self.depth

    def __iter__(self) -> Iterator[float]:
        """Allow iteration over the dimensions."""
        return iter((self.width, self.height, self.depth))

    def __repr__(self) -> str:
        """Return a string representation of the Size3D."""
        return (
            f"Size3D(w={self.width:.1f},"
            f" h={self.height:.1f}, d={self.depth:.1f})"
        )


"""
jermiah (01/30/2025): 
not sure about this direction class, was an initial proof-of-concept
doesnt seem like a dealbreaker to need, havent dealt with any issues
Really only wanted to use it for docs/tutorials to show how images
are oriented + work via directions for sitk.Image

lets not consider it too much unless we need to debug with it
"""


@dataclass(frozen=True, eq=True)
class Direction:
    """
    Represent a directional matrix for image orientation.

    Supports 3D (3x3) directional matrices in row-major format.

    Attributes
    ----------
    matrix : Tuple[float, ...]
        A flattened 1D array representing the matrix,
        with length 9 (3x3).
    """

    matrix: Matrix3DFlat

    def __post_init__(self) -> None:
        length = len(self.matrix)
        if length != 9:
            msg = (
                "Direction must be a 3x3 (9 values) matrix."
                f" Got {length} values."
            )
            raise ValueError(msg)

    @classmethod
    def from_matrix(
        cls,
        matrix: Matrix3D,
    ) -> Direction:
        """
        Create a Direction object from a full 3D (3x3) matrix.

        Parameters
        ----------
        matrix : Matrix3D
            A nested tuple representing the 3D matrix.

        Returns
        -------
        Direction
            A Direction instance.
        """
        if (size := len(matrix)) != 3:
            msg = f"Matrix must be 3x3. Got {size=}."
            raise ValueError(msg)
        for row in matrix:
            if len(row) != size:
                raise ValueError("Matrix must be square (3x3).")
        flattened: FlattenedMatrix = tuple(
            value for row in matrix for value in row
        )  # type: ignore
        return cls(matrix=flattened)

    def to_matrix(self) -> list[list[float]]:
        """Convert the flattened row-major array back to a 3D matrix."""
        dim = 3
        return [list(self.matrix[i * dim : (i + 1) * dim]) for i in range(dim)]

    def normalize(self) -> Direction:
        """Return a new Direction with normalized row vectors."""
        matrix = self.to_matrix()
        normalized_matrix = [
            list(np.array(row) / np.linalg.norm(row)) for row in matrix
        ]
        return Direction.from_matrix(
            tuple(tuple(row) for row in normalized_matrix)  # type: ignore
        )

    def is_normalized(self, tol: float = 1e-6) -> bool:
        """Check if the row vectors of the matrix are normalized."""
        matrix = self.to_matrix()
        for row in matrix:
            if not np.isclose(np.linalg.norm(row), 1.0, atol=tol):
                return False
        return True

    def __iter__(self) -> Iterator:
        """Allow the Direction instance to be passed directly as a 1D array."""
        yield from self.matrix

    def __repr__(self) -> str:
        dim = 3
        rows = self.to_matrix()
        formatted_rows = [
            "  [" + ", ".join(f"{value:>7.3f}" for value in row) + "]"
            for row in rows
        ]
        return (
            f"Direction(  {dim}x{dim} matrix\n"
            + "\n".join(formatted_rows)
            + f"\n)"
        )


if __name__ == "__main__":
    # ruff : noqa
    from pathlib import Path
    from rich import print

    ########################################
    # Vector3D
    ########################################

    vector1 = Vector3D(1.0, 2.0, 3.0)

    vector2 = Vector3D((1.0, 2.0, 3.0))  # as tuple input
    assert all((attr1 == attr2) for attr1, attr2 in zip(vector1, vector2))

    for attr in vector1:
        print(attr)

    print(vector1)

    ########################################
    # Coordinate3D
    ########################################

    point = Coordinate3D(10.0, 20.0, 30.0)
    point2 = Coordinate3D((15.0, 25.0, 35.0))

    print(point)
    print(point2)

    size_tuple = (50.0, 60.0, 70.0)
    size = Size3D(size_tuple)
    point_plus_size = point + size_tuple

    print(f"Adding {point=} and {size_tuple=} = {point_plus_size}")
    print(f"Adding {point=} and {size=} = {point + size}")

    # Create instances of each class
    # point = Point3D(10.0, 20.0, 30.0)
    # size = Size3D(50.0, 60.0, 70.0)
    # direction = Direction.from_matrix(
    #     (
    #         (0.707, 0.707, 0.0),
    #         (-0.707, 0.707, 0.0),
    #         (0.0, 0.0, 1.0),
    #     )
    # )

    # # Testing Point3D and Size3D operations
    # new_point = point + size

    # # Printing out the details
    # print(f"Point: {point}")
    # print(f"Size: {size}")
    # print(f"New point after adding size: {new_point}")
    # print(f"Direction: {direction}")

    # # Unpacking the values
    # print("Unpacked Point:", tuple(point))  # (10.0, 20.0, 30.0)
    # print("Unpacked Size:", tuple(size))  # (50.0, 60.0, 70.0)

    # example_image = np.random.rand(10, 10, 10)
    # example_sitk_image = sitk.GetImageFromArray(example_image)

    # # Create a direction vector
    # # 3x3 Direction Matrix
    # direction_3d = Direction.from_matrix(
    #     (
    #         (0.707, 0.707, 0.0),
    #         (-0.707, 0.707, 0.0),
    #         (0.0, 0.0, 1.0),
    #     )
    # )

    # print(f"{direction_3d=}")
    # example_sitk_image.SetDirection(direction_3d)

    # # make another direction from a flattened
    # direction_3d_flat = Direction(
    #     matrix=(0.707, 0.707, 0.0, -0.707, 0.707, 0.0, 0.0, 0.0, 1.0)
    # )
    # print(f"{direction_3d_flat=}")
    # print(f"{(direction_3d_flat==direction_3d)=}")

    # print(f"{example_sitk_image=}")
