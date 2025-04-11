import pytest
import numpy as np

from imgtools.coretypes.spatial_types.direction import Direction, Matrix3D, Matrix3DFlat

def test_direction_init_valid():
    """Ensure a valid 9-element tuple creates a Direction."""
    valid_tuple: Matrix3DFlat = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0)
    dir_obj = Direction(matrix=valid_tuple)
    assert dir_obj.matrix == valid_tuple


def test_direction_init_invalid():
    """Check that passing a tuple with fewer/more than 9 elements raises ValueError."""
    invalid_tuple = (1.0, 2.0)  # Only 2 elements
    with pytest.raises(ValueError) as exc_info:
        _ = Direction(matrix=invalid_tuple)  # type: ignore
    assert "must be a 3x3 (9 values) matrix" in str(exc_info.value)


def test_from_matrix_valid():
    """Ensure from_matrix accepts a proper 3x3 structure."""
    valid_matrix: Matrix3D = (
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    )
    dir_obj = Direction.from_matrix(valid_matrix)
    expected_flat = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
    assert dir_obj.matrix == expected_flat


def test_from_matrix_wrong_size():
    """Check that from_matrix raises ValueError for non-3x3 input."""
    invalid_matrix = ((1.0, 2.0), (3.0, 4.0))  # 2x2 instead of 3x3
    with pytest.raises(ValueError) as exc_info:
        _ = Direction.from_matrix(invalid_matrix)  # type: ignore
    assert "Matrix must be 3x3" in str(exc_info.value)


def test_to_matrix():
    """Verify to_matrix returns a 3x3 nested list correctly."""
    flat: Matrix3DFlat = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0)
    dir_obj = Direction(matrix=flat)
    matrix_2d = dir_obj.to_matrix()
    assert matrix_2d == [
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 6.0],
        [7.0, 8.0, 9.0],
    ]


def test_normalize():
    """Check that normalize gives rows a unit norm."""
    flat: Matrix3DFlat = (2.0, 0.0, 0.0, 0.0, 4.0, 0.0, 0.0, 0.0, 6.0)
    dir_obj = Direction(matrix=flat)
    norm_obj = dir_obj.normalize()
    # After normalization, each row should have length 1
    assert norm_obj.is_normalized()
    # Original should remain unchanged because Direction is immutable
    assert not dir_obj.is_normalized()


def test_is_normalized_true():
    """Test is_normalized returns True when all rows are unit vectors."""
    unit_flat: Matrix3DFlat = (
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0,
        0.0, 0.0, 1.0
    )
    dir_obj = Direction(matrix=unit_flat)
    assert dir_obj.is_normalized()


def test_is_normalized_false():
    """Test is_normalized returns False when any row is not a unit vector."""
    flat: Matrix3DFlat = (
        1.0, 1.0, 0.0,  # norm = sqrt(2)
        0.0, 1.0, 0.0,  # norm = 1
        0.0, 0.0, 1.0   # norm = 1
    )
    dir_obj = Direction(matrix=flat)
    assert not dir_obj.is_normalized()


def test_iteration():
    """Check that we can iterate over all nine matrix elements."""
    flat: Matrix3DFlat = (
        1.0, 2.0, 3.0,
        4.0, 5.0, 6.0,
        7.0, 8.0, 9.0
    )
    dir_obj = Direction(matrix=flat)
    collected = list(dir_obj)
    assert collected == list(flat)


def test_repr():
    """Smoke test for __repr__, ensuring it returns a string with some key content."""
    flat: Matrix3DFlat = (
        1.0, 2.0, 3.0,
        4.0, 5.0, 6.0,
        7.0, 8.0, 9.0
    )
    dir_obj = Direction(matrix=flat)
    out = repr(dir_obj)
    assert isinstance(out, str)
    assert "Direction(" in out
    # Quick check that some part of the data is in there
    assert "[1.00,2.00,3.00]" in out