from typing import Tuple

import pytest

from imgtools.coretypes import (
    Coordinate3D,
    Size3D,
    Spacing3D,
)


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

    def test_truediv(self) -> None:
        """Test Spacing3D division with a scalar.
        
        ALWAYS divides as floor division.
        """
        s = Size3D(10, 20, 30)
        scalar = 2
        result = s / scalar
        assert result == Size3D(5, 10, 15)
        assert isinstance(result, Size3D)
        assert result.volume == 750

        # test that floordivision is used
        result2 = s // scalar
        assert result2 == Size3D(5, 10, 15)
        assert isinstance(result2, Size3D)

        nonuniformscalar = 3
        result3 = s / nonuniformscalar
        assert result3 == Size3D(3, 6, 10)

        # divide by another Size3D
        s2 = Size3D(2, 4, 6)
        result4 = s / s2
        assert result4 == Size3D(5, 5, 5)
        assert isinstance(result4, Size3D)
        assert result4.volume == 125

        # divide by a tuple
        tuple_s = (2, 4, 6)
        result5 = s / tuple_s
        assert result5 == Size3D(5, 5, 5)
        assert isinstance(result5, Size3D)



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

    def test_invalid_initialization(self) -> None:
        """Ensure Coordinate3D raises errors for invalid inputs."""
        with pytest.raises(ValueError):
            Coordinate3D(1, 2)

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

    def test_indexing(self) -> None:
        """Test indexing access via int and str."""
        c = Coordinate3D(1, 2, 3)
        assert c[0] == 1
        assert c[1] == 2
        assert c[2] == 3
        assert c["x"] == 1
        assert c["y"] == 2
        assert c["z"] == 3
        with pytest.raises(IndexError):
            _ = c[3]
        with pytest.raises(IndexError):
            _ = c["invalid"]

    def test_equality(self) -> None:
        """Test equality comparison for Coordinate3D."""
        c1 = Coordinate3D(1, 2, 3)
        c2 = Coordinate3D(1, 2, 3)
        c3 = Coordinate3D(4, 5, 6)
        assert c1 == c2
        assert c1 != c3

    def test_comparison(self) -> None:
        """Test comparison operations for Coordinate3D."""
        c1 = Coordinate3D(1, 2, 3)
        c2 = Coordinate3D(4, 5, 6)
        assert c1 < c2
        assert c2 > c1

    def test_repr(self) -> None:
        """Ensure Coordinate3D has a readable representation."""
        c = Coordinate3D(1, 2, 3)
        assert repr(c) == "Coordinate3D(x=1, y=2, z=3)"


class TestSpacing3D:
    """Test suite for Spacing3D class."""

    @pytest.mark.parametrize(
        "args, expected",
        [
            # Float values
            ((1.0, 2.0, 3.0), (1.0, 2.0, 3.0)),
            # Tuple input
            (((4.0, 5.0, 6.0),), (4.0, 5.0, 6.0)),
        ],
    )
    def test_initialization(
        self,
        args: Tuple[float, ...],
        expected: Tuple[float, float, float],
    ) -> None:
        """Test Spacing3D initialization."""
        sp = Spacing3D(*args)
        assert (sp.x, sp.y, sp.z) == expected

    def test_invalid_initialization(self) -> None:
        """Ensure Spacing3D raises errors for invalid inputs."""
        with pytest.raises(ValueError):
            Spacing3D(1.0, 2.0)

    def test_iteration(self) -> None:
        """Ensure Spacing3D is iterable."""
        sp = Spacing3D(1.0, 2.0, 3.0)
        assert list(sp) == [1.0, 2.0, 3.0]

    def test_repr(self) -> None:
        """Ensure Spacing3D has a readable representation."""
        sp = Spacing3D(1.0, 2.0, 3.0)
        assert repr(sp) == "Spacing3D(x=1.0, y=2.0, z=3.0)"
