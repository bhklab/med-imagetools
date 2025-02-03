from typing import Tuple, Union

import pytest

from imgtools import (
    Coordinate3D,
    Size3D,
    Spacing3D,
    Vector3D,
)


class TestVector3D:
    """Test suite for Vector3D class."""

    @pytest.mark.parametrize(
        "args, expected",
        [
            # Integer values
            ((1, 2, 3), (1, 2, 3)),
            # Tuple input
            (((4, 5, 6),), (4, 5, 6)),
        ],
    )
    def test_initialization(
        self,
        args: Tuple[int, ...],
        expected: Tuple[int, int, int],
    ) -> None:
        """Test Vector3D initialization with different input types."""
        v = Vector3D(*args)
        assert (v.x, v.y, v.z) == expected
        assert (
            isinstance(v.x, int)
            and isinstance(v.y, int)
            and isinstance(v.z, int)
        )

    @pytest.mark.parametrize(
        "invalid_args",
        [
            (1, 2),  # Too few values
            (1, 2, 3, 4),  # Too many values
        ],
    )
    def test_invalid_initialization(
        self, invalid_args: Tuple[Union[int, str], ...]
    ) -> None:
        """Ensure Vector3D raises errors for invalid inputs."""
        with pytest.raises(ValueError):
            Vector3D(*invalid_args)  # type: ignore

    def test_indexing(self) -> None:
        """Test indexing access via int and str."""
        v = Vector3D(1, 2, 3)
        assert v[0] == 1
        assert v[1] == 2
        assert v[2] == 3
        assert v["x"] == 1
        assert v["y"] == 2
        assert v["z"] == 3
        with pytest.raises(IndexError):
            _ = v[3]
        with pytest.raises(IndexError):
            _ = v["invalid"]

    def test_iteration(self) -> None:
        """Ensure Vector3D is iterable."""
        v = Vector3D(1, 2, 3)
        assert list(v) == [1, 2, 3]

        for i, val in enumerate(v, start=1):
            assert val == i

    def test_repr(self) -> None:
        """Ensure Vector3D has a readable representation."""
        v = Vector3D(1, 2, 3)
        assert repr(v) == "Vector3D(x=1, y=2, z=3)"


class TestSize3D:
    """Test suite for Size3D class."""

    @pytest.mark.parametrize(
        "args, expected",
        [
            # Integer values
            ((1, 2, 3), (1, 2, 3)),
            # Tuple input
            (((4, 5, 6),), (4, 5, 6)),
        ],
    )
    def test_initialization(
        self,
        args: Tuple[int, ...],
        expected: Tuple[int, int, int],
    ) -> None:
        """Test Size3D initialization with different input types."""
        s = Size3D(*args)
        assert (s.width, s.height, s.depth) == expected

    def test_invalid_initialization(self) -> None:
        """Ensure Size3D raises errors for invalid inputs."""
        with pytest.raises(ValueError):
            Size3D(1, 2)

    def test_volume(self) -> None:
        """Ensure Size3D correctly calculates volume."""
        s = Size3D(3, 4, 5)
        assert s.volume == 60

    def test_iteration(self) -> None:
        """Ensure Size3D is iterable."""
        s = Size3D(1, 2, 3)
        assert list(s) == [1, 2, 3]

    def test_repr(self) -> None:
        """Ensure Size3D has a readable representation."""
        s = Size3D(1, 2, 3)
        assert repr(s) == "Size3D(w=1, h=2, d=3)"


class TestCoordinate3D:
    """Test suite for Coordinate3D class."""

    @pytest.mark.parametrize(
        "args, expected",
        [
            # Integer values
            ((1, 2, 3), (1, 2, 3)),
            # Tuple input
            (((4, 5, 6),), (4, 5, 6)),
        ],
    )
    def test_initialization(
        self,
        args: Tuple[int, ...],
        expected: Tuple[int, int, int],
    ) -> None:
        """Test Coordinate3D initialization."""
        c = Coordinate3D(*args)
        assert (c.x, c.y, c.z) == expected

    def test_addition(self) -> None:
        """Test Coordinate3D addition with Size3D."""
        c = Coordinate3D(10, 20, 30)
        s = Size3D(1, 2, 3)
        assert (c + s) == Coordinate3D(11, 22, 33)

        c2 = Coordinate3D(10, 20, 30)
        new = c + c2
        assert new == Coordinate3D(20, 40, 60)

        # we also let users add tuples, just for the sake of it
        tuple_c = (10, 20, 30)
        new_with_tuple = c + tuple_c
        assert new_with_tuple == Coordinate3D(20, 40, 60)

    def test_subtraction(self) -> None:
        """Test Coordinate3D subtraction with Size3D."""
        c = Coordinate3D(10, 20, 30)
        s = Size3D(1, 2, 3)
        assert (c - s) == Coordinate3D(9, 18, 27)

        c2 = Coordinate3D(10, 20, 30)
        new = c - c2
        assert new == Coordinate3D(0, 0, 0)

        # we also let users subtract tuples, just for the sake of it
        tuple_c = (10, 20, 30)
        new_with_tuple = c - tuple_c
        assert new_with_tuple == Coordinate3D(0, 0, 0)

    def test_invalid_operations(self) -> None:
        """Ensure Coordinate3D raises errors for unsupported operations."""
        c = Coordinate3D(10, 20, 30)
        with pytest.raises(TypeError):
            _ = c + "invalid"  # type: ignore
        with pytest.raises(TypeError):
            _ = c - (1, 2)  # type: ignore

    def test_iteration(self) -> None:
        """Ensure Coordinate3D is iterable."""
        c = Coordinate3D(1, 2, 3)
        assert list(c) == [1, 2, 3]


class TestSpacing3D:
    """Test suite for Spacing3D class."""

    @pytest.mark.parametrize(
        "args, expected",
        [
            # Integer values
            ((1, 2, 3), (1, 2, 3)),
            # Tuple input
            (((4, 5, 6),), (4, 5, 6)),
        ],
    )
    def test_initialization(
        self,
        args: Tuple[int, ...],
        expected: Tuple[int, int, int],
    ) -> None:
        """Test Spacing3D initialization."""
        sp = Spacing3D(*args)
        assert (sp.x, sp.y, sp.z) == expected
