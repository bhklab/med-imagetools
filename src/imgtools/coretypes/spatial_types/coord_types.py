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

"""

from __future__ import annotations

from dataclasses import dataclass
from functools import total_ordering

from typing import Iterator


@dataclass
@total_ordering
class Coordinate3D:
    """
    Represent a point in 3D space.

    Can add and subtract other Point3D or Size3D objects.


    Attributes
    ----------
    x : int
        X-component of the vector.
    y : int
        Y-component of the vector.
    z : int
        Z-component of the vector.

    Methods
    -------
    __add__(other):
        Add another Coordinate3D to this vector.
    __sub__(other):
        Subtract another Coordinate3D from this vector.
    __iter__():
        Iterate over the components (x, y, z).
    __getitem__(index):
        Access components via index.
    """

    x: int
    y: int
    z: int

    def __init__(self, *args: int) -> None:
        """Initialize a Coordinate3D with x, y, z components."""
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

    def to_tuple(self) -> tuple[int, int, int]:
        """Return the (x, y, z) tuple representation.

        Returns
        -------
        tuple of int
            The coordinate as (x, y, z).
        """
        return (self.x, self.y, self.z)

    def __iter__(self) -> Iterator[int]:
        """Allow iteration over the components."""
        return iter((self.x, self.y, self.z))

    def __getitem__(self, idx: int | str) -> int:
        """Access components via index."""
        match idx:
            case int() as idx:
                return (self.x, self.y, self.z)[idx]
            case str() if idx in vars(self):
                return getattr(self, idx)
            case _:
                errmsg = f"Invalid index: {idx}."
                raise IndexError(errmsg)

    def __repr__(self) -> str:
        """Return a string representation of the Coordinate3D."""
        cls = self.__class__.__name__
        return f"{cls}(x={self.x}, y={self.y}, z={self.z})"

    def __eq__(self, other: object) -> bool:
        """Check if two Coordinate3D objects are equal."""
        if not isinstance(other, Coordinate3D):
            errmsg = (
                f"Cannot compare {self.__class__.__name__} with {type(other)}."
            )
            raise TypeError(errmsg)
        return (self.x, self.y, self.z) == (other.x, other.y, other.z)

    def __lt__(self, other: Coordinate3D) -> bool:
        """Check if this Coordinate3D is less than another."""
        if not isinstance(other, Coordinate3D):
            return NotImplemented
        return (self.x, self.y, self.z) < (other.x, other.y, other.z)

    def __add__(
        self, other: int | Coordinate3D | Size3D | tuple
    ) -> Coordinate3D:
        """Add another Coordinate3D to this vector."""
        match other:
            case int() as value:
                return Coordinate3D(
                    self.x + value, self.y + value, self.z + value
                )
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
                    " Expected int, Coordinate3D, or Size3D."
                )
                raise TypeError(errmsg)

    def __sub__(
        self, other: int | Coordinate3D | Size3D | tuple
    ) -> Coordinate3D:
        """Subtract another Coordinate3D from this vector."""
        match other:
            case int() as value:
                return Coordinate3D(
                    self.x - value, self.y - value, self.z - value
                )
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
                    " Expected int, Coordinate3D, or Size3D."
                )
                raise TypeError(errmsg)


class Spacing3D:
    """Represent the spacing in 3D space."""

    x: float
    y: float
    z: float

    def __init__(self, *args: float) -> None:
        """Initialize a Spacing3D with x, y, z components."""
        match args:
            case [x, y, z]:
                self.x, self.y, self.z = x, y, z
            case [tuple_points] if isinstance(tuple_points, tuple):
                if len(tuple_points) != 3:
                    errmsg = (
                        f"{self.__class__.__name__} expects 3 values for x, y, z."
                        f" Got {len(tuple_points)} values for {tuple_points}."
                    )
                    raise ValueError(errmsg)
                self.x, self.y, self.z = tuple_points
            case _:
                errmsg = (
                    f"{self.__class__.__name__} expects 3 values for x, y, z."
                    f" Got {len(args)} values for {args}."
                )
                raise ValueError(errmsg)

    def __repr__(self) -> str:
        """Return a string representation of the Spacing3D."""
        return f"Spacing3D(x={self.x}, y={self.y}, z={self.z})"

    def __iter__(self) -> Iterator[float]:
        """Allow iteration over the components."""
        return iter((self.x, self.y, self.z))

    def to_tuple(self) -> tuple[float, float, float]:
        """Return the (x, y, z) spacing as a tuple.

        Returns
        -------
        tuple of float
            The spacing as (x, y, z).
        """
        return (self.x, self.y, self.z)


@dataclass
class Size3D:
    """
    Represent the size (width, height, depth) of a 3D object.

    Attributes
    ----------
    width : int
        The width of the 3D object.
    height : int
        The height of the 3D object.
    depth : int
        The depth of the 3D object.

    Methods
    -------
    volume:
        Calculate the volume of the 3D object.
    """

    width: int
    height: int
    depth: int

    def __init__(self, *args: int) -> None:
        match args:
            case [int() as width, int() as height, int() as depth]:
                self.width, self.height, self.depth = width, height, depth
            case [tuple_points] if isinstance(tuple_points, tuple):
                self.width, self.height, self.depth = map(int, tuple_points)
            case _:
                errmsg = (
                    f"{self.__class__.__name__} expects 3 integer values for width, height, depth."
                    f" Got {len(args)} values for {args}."
                )
                raise ValueError(errmsg)

    @property
    def volume(self) -> int:
        """Calculate the volume of the 3D object."""
        return self.width * self.height * self.depth

    def to_tuple(self) -> tuple[int, int, int]:
        """Return the (width, height, depth) tuple representation.

        Returns
        -------
        tuple of int
            The size as (width, height, depth).
        """
        return (self.width, self.height, self.depth)

    def __iter__(self) -> Iterator[int]:
        """Allow iteration over the dimensions."""
        return iter((self.width, self.height, self.depth))

    def __repr__(self) -> str:
        """Return a string representation of the Size3D."""
        return f"Size3D(w={self.width}, h={self.height}, d={self.depth})"

    def __truediv__(self, other: int | Size3D | tuple) -> Size3D:
        """
        Divide a Size3D by an integer, Size3D, or 3-tuple using floor division.

        Divides each dimension (width, height, depth) by the corresponding value from
        the divisor. If the divisor is an integer, all dimensions are divided uniformly.
        If a Size3D or a 3-tuple is provided, each dimension is divided by its counterpart.
        Division is carried out using floor division (//) so that the result remains an integer.

        Parameters
        ----------
            other: The divisor, which can be an int, a Size3D instance, or a tuple of
                   three integers representing (width, height, depth).

        Returns
        -------
            A new Size3D instance with dimensions divided by the given divisor.

        Raises
        ------
            TypeError: If the divisor is not an int, Size3D, or a 3-tuple.

        Examples
        --------
            >>> size = Size3D(10, 20, 30)
            >>> size / 3
            Size3D(w=3, h=6, d=10)
            >>> size / Size3D(2, 4, 6)
            Size3D(w=5, h=5, d=5)
        """
        match other:
            case int() as value:
                return Size3D(
                    self.width // value,
                    self.height // value,
                    self.depth // value,
                )
            case Size3D(width, height, depth):
                return Size3D(
                    self.width // width,
                    self.height // height,
                    self.depth // depth,
                )
            case tuple() if len(other) == 3:
                return Size3D(
                    self.width // other[0],
                    self.height // other[1],
                    self.depth // other[2],
                )
            case _:
                errmsg = (
                    f"Unsupported type for division: {type(other)}."
                    " Expected int, tuple, or Size3D."
                )
                raise TypeError(errmsg)

    def __floordiv__(self, other: int | Size3D | tuple) -> Size3D:
        """
        Perform floor division on a Size3D instance.

        Returns a new Size3D with each dimension calculated using floor division by the provided
        divisor. The divisor may be an integer, a Size3D instance, or a tuple of three integers.
        This method delegates to __truediv__, which handles input validation and performs the actual
        division.
        """
        return self.__truediv__(
            other
        )  # Since truediv already uses // operator


if __name__ == "__main__":  # pragma: no cover
    # ruff : noqa
    from pathlib import Path
    from rich import print

    ########################################
    # Vector3D
    ########################################
    myint = 10
    print(myint)

    vector1 = Coordinate3D(1, 2, 3)

    # as tuple input
    vector1_same = Coordinate3D(*(1, 2, 3))
    assert all((attr1 == attr2) for attr1, attr2 in zip(vector1, vector1_same))

    vector2 = Coordinate3D(*(1, 2, 4))

    print(f"{(vector1 == vector2)=}")
    print(f"{(vector1 < vector2)=}")
    print(f"{(vector1 > vector2)=}")

    # access object attributes via [ ]
    print(f"{vector1[0]=}")
    print(f"{vector1['y']=}")

    ########################################
    # Coordinate3D
    ########################################

    point = Coordinate3D(10, 20, 30)
    point2 = Coordinate3D(
        (15, 25, 35)  # type: ignore
    )  # mypy will complain about this, but it will work
    point2 = Coordinate3D(
        *(15, 25, 35)
    )  # unpack the tuple to avoid mypy error

    print(point)
    print(point2)

    size_tuple = (50, 60, 70)
    size = Size3D(
        size_tuple  # type: ignore
    )  # mypy will complain about this, but it will work
    size = Size3D(*size_tuple)  # unpack the tuple
    point_plus_size = point + size_tuple

    print(f"Adding {point=} and {size_tuple=} = {point_plus_size}")
    print(f"Adding {point=} and {size=} = {point + size}")

    # make a sitk image
    import SimpleITK as sitk

    # create a 3D image
    image = sitk.Image(100, 100, 100, sitk.sitkInt16)

    image_size = Size3D(*image.GetSize())
    print(f"Image size: {image_size}")

    # get the spacing
    image_spacing = Spacing3D(*image.GetSpacing())
    print(f"Image spacing: {image_spacing}")
