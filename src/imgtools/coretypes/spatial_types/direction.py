"""
This module defines the Direction class, which stores a 3x3 orientation
matrix as a flattened tuple of nine floats (row-major order). You can
convert it to a 3x3 structure, normalize row vectors, or check if rows
are normalized.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Tuple, TypeAlias

import numpy as np

"""
jermiah (01/30/2025): 
not sure about this direction class, was an initial proof-of-concept
doesnt seem like a dealbreaker to need, havent dealt with any issues
Really only wanted to use it for docs/tutorials to show how images
are oriented + work via directions for sitk.Image

lets not consider it too much unless we need to debug with it
"""

Matrix3D: TypeAlias = Tuple[
    Tuple[float, float, float],
    Tuple[float, float, float],
    Tuple[float, float, float],
]
Matrix3DFlat: TypeAlias = Tuple[
    float, float, float, float, float, float, float, float, float
]

FlattenedMatrix = Matrix3DFlat


@dataclass(frozen=True, eq=True)
class Direction:
    """Represent a directional matrix for image orientation.

    Supports 3D (3x3) directional matrices in row-major format as 9 floats.
    It's often useful when you need to keep track of orientation data
    in a compact way.

    Attributes
    ----------
    matrix : Matrix3DFlat
        Flattened representation of a 3x3 matrix.
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
        Create a Direction instance from a nested 3x3 tuple.

        Parameters
        ----------
        matrix : Matrix3D
            A tuple of 3 rows, each row having 3 floats.

        Returns
        -------
        Direction
            An instance with the flattened matrix.

        Raises
        ------
        ValueError
            If the input isn't a 3x3 structure.
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

    def flip_axis(self, axis: int) -> Direction:
        """Flip the matrix along a specified axis.

        Parameters
        ----------
        axis : int
            The axis to flip (0, 1, or 2).

        Returns
        -------
        Direction
            A new instance with the flipped matrix.
        """
        if axis not in (0, 1, 2):
            raise ValueError("Axis must be 0 (x), 1 (y), or 2 (z).")
        matrix = self.to_matrix()
        matrix[axis] = [-v for v in matrix[axis]]
        return Direction.from_matrix(
            tuple(tuple(row) for row in matrix)  # type: ignore
        )

    def to_matrix(self) -> list[list[float]]:
        """Convert the flattened row-major array back to a 3D matrix.

        Returns
        -------
        list of list of float
            The 3x3 data, row by row.
        """
        dim = 3
        return [list(self.matrix[i * dim : (i + 1) * dim]) for i in range(dim)]

    def normalize(self) -> Direction:
        """Return a new Direction with normalized row vectors.

        Zero rows remain unchanged.

        Returns
        -------
        Direction
            A new instance with normalized rows.
        """
        matrix = self.to_matrix()
        normalized_matrix = [
            list(np.array(row) / np.linalg.norm(row)) for row in matrix
        ]
        return Direction.from_matrix(
            tuple(tuple(row) for row in normalized_matrix)  # type: ignore
        )

    def is_normalized(self, tol: float = 1e-6) -> bool:
        """Check if all values are (almost) 1, given a tolerance.

        Parameters
        ----------
        tol : float, optional
            Acceptable deviation from 1.

        Returns
        -------
        bool
            True if all rows meet the norm requirement, else False.
        """
        matrix = self.to_matrix()
        for row in matrix:
            if not np.isclose(np.linalg.norm(row), 1.0, atol=tol):
                return False
        return True

    def __iter__(self) -> Iterator:
        """Allow the Direction instance to be passed directly as a 1D array."""
        yield from self.matrix

    def __repr__(self) -> str:
        rows = self.to_matrix()
        formatted_rows = [
            "[" + ",".join(f"{value:>4.2f}" for value in row) + "]"
            for row in rows
        ]
        return f"Direction({', '.join(formatted_rows)})"

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
