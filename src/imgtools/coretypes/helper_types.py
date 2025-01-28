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
>>> direction = Direction(i=1.0, j=0.0, k=0.0)
"""

from __future__ import annotations

import numpy as np
import SimpleITK as sitk
from dataclasses import dataclass

from typing import Tuple, Iterable, TypeAlias
import numpy as np

Matrix2D: TypeAlias = Tuple[Tuple[float, float], Tuple[float, float]]
Matrix3D: TypeAlias = Tuple[
    Tuple[float, float, float],
    Tuple[float, float, float],
    Tuple[float, float, float],
]
Matrix2DFlat: TypeAlias = Tuple[float, float, float, float]
Matrix3DFlat: TypeAlias = Tuple[
    float, float, float, float, float, float, float, float, float
]

FlattenedMatrix = Matrix2DFlat | Matrix3DFlat


@dataclass(frozen=True)
class Direction:
    """
    Represent a directional matrix for image orientation.

    Supports 2D (2x2) and 3D (3x3) directional matrices in row-major format.

    Attributes
    ----------
    matrix : Tuple[float, ...]
        A flattened 1D array representing the matrix,
        with length 4 (2x2) or 9 (3x3).
    """

    matrix: Matrix2DFlat | Matrix3DFlat

    def __post_init__(self) -> None:
        length = len(self.matrix)
        if length not in (4, 9):
            msg = (
                "Direction must be a 2x2 (4 values) or 3x3 (9 values) matrix."
                f" Got {length} values."
            )
            raise ValueError(msg)

    def is_normalized(self, tol: float = 1e-6) -> bool:
        """Check if the row vectors of the matrix are normalized."""
        matrix = self.to_matrix()
        for row in matrix:
            if not np.isclose(np.linalg.norm(row), 1.0, atol=tol):
                return False
        return True

    @classmethod
    def from_matrix(
        cls,
        matrix: Matrix2D | Matrix3D,
    ) -> Direction:
        """
        Create a Direction object from a full 2D (2x2) or 3D (3x3) matrix.

        Parameters
        ----------
        matrix : Matrix2D | Matrix3D
            A nested tuple representing the 2D or 3D matrix.

        Returns
        -------
        Direction
            A Direction instance.
        """
        size = len(matrix)
        if size not in (2, 3):
            raise ValueError("Matrix must be 2x2 or 3x3.")
        for row in matrix:
            if len(row) != size:
                raise ValueError("Matrix must be square (2x2 or 3x3).")
        flattened: FlattenedMatrix = tuple(
            value for row in matrix for value in row
        )  # type: ignore
        return cls(matrix=flattened)

    def to_matrix(self) -> list[list[float]]:
        """Convert the flattened row-major array back to a 2D or 3D matrix."""
        dim = int(len(self.matrix) ** 0.5)
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

    def __iter__(self) -> Iterable:
        """Allow the Direction instance to be passed directly as a 1D array."""
        yield from self.matrix

    def __repr__(self) -> str:
        dim = int(len(self.matrix) ** 0.5)
        rows = self.to_matrix()
        return (
            f"Direction(\n"
            + "\n".join([f"  {row}" for row in rows])
            + f"\n  {dim}x{dim} matrix, row-major\n)"
        )


if __name__ == "__main__":
    # ruff : noqa
    from pathlib import Path
    from rich import print

    from imgtools.io import read_dicom_series

    # p = "/home/bioinf/bhklab/radiomics/repos/med-image_test-data/procdata/NSCLC-Radiomics/LUNG1-002/1.3.6.1.4.1.32722.99.99.232988001551799080335895423941323261228"

    # # ct_path = Path(p)
    # ct_path = p

    # ct_series = read_dicom_series(ct_path)

    # print(f'{ct_series["direction"]=}')

    example_image = np.random.rand(10, 10, 10)
    example_sitk_image = sitk.GetImageFromArray(example_image)

    # Create a direction vector
    # 3x3 Direction Matrix
    direction_3d = Direction.from_matrix(
        (
            (0.707, 0.707, 0.0),
            (-0.707, 0.707, 0.0),
            (0.0, 0.0, 1.0),
        )
    )

    print(f"{example_sitk_image.GetDirection()=}")
    print(f"{direction_3d=}")
    example_sitk_image.SetDirection(direction_3d)
    print(f"{example_sitk_image.GetDirection()=}")
