import numpy as np
import pytest
import SimpleITK as sitk
from numpy._typing._array_like import NDArray

from imgtools.utils.imageutils import (
    array_to_image,
    idxs_to_physical_points,
    image_to_array,
    physical_points_to_idxs,
)


@pytest.mark.parametrize(
    "array, origin, direction, spacing, reference_image",
    [
        (
            np.zeros((10, 10, 10)),
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
            (1.0, 1.0, 1.0),
            None,
        ),
        (
            np.ones((5, 5, 5)),
            (1.0, 1.0, 1.0),
            (0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0),
            (0.5, 0.5, 0.5),
            None,
        ),
    ],
)
def test_array_to_image(
    array: np.ndarray,
    origin: tuple[float, float, float],
    direction: tuple[
        float, float, float, float, float, float, float, float, float
    ],
    spacing: tuple[float, float, float],
    reference_image: sitk.Image | None,
) -> None:
    image = array_to_image(array, origin, direction, spacing, reference_image)
    assert isinstance(image, sitk.Image)
    assert image.GetOrigin() == origin
    assert image.GetDirection() == direction
    assert image.GetSpacing() == spacing


@pytest.mark.parametrize(
    "image",
    [
        sitk.Image([10, 10, 10], sitk.sitkUInt8),
        sitk.Image([5, 5, 5], sitk.sitkFloat32),
    ],
)
def test_image_to_array(image: sitk.Image) -> None:
    assert isinstance(image, sitk.Image)
    array, origin, direction, spacing = image_to_array(image)
    assert isinstance(array, np.ndarray)
    assert origin == image.GetOrigin()
    assert direction == image.GetDirection()
    assert spacing == image.GetSpacing()


@pytest.mark.parametrize(
    "image, points, continuous",
    [
        (
            sitk.Image([10, 10, 10], sitk.sitkUInt8),
            [np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])],
            False,
        ),
        (
            sitk.Image([5, 5, 5], sitk.sitkFloat32),
            [np.array([[2.0, 2.0, 2.0], [3.0, 3.0, 3.0]])],
            True,
        ),
    ],
)
def test_physical_points_to_idxs(
    image: sitk.Image,
    points: list[np.ndarray],
    continuous: bool,
) -> None:
    idxs = physical_points_to_idxs(image, points, continuous)
    assert isinstance(idxs, list)
    for idx in idxs:
        assert isinstance(idx, np.ndarray)


@pytest.mark.parametrize(
    "image, idxs, expected_points",
    [
        (
            sitk.Image([10, 10, 10], sitk.sitkUInt8),
            np.array([[0, 0, 0], [1, 1, 1]]),
            np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]),
        ),
        (
            sitk.Image([5, 5, 5], sitk.sitkFloat32),
            np.array([[2, 2, 2], [3, 3, 3]]),
            np.array([[2.0, 2.0, 2.0], [3.0, 3.0, 3.0]]),
        ),
    ],
)
def test_idxs_to_physical_points(
    image: sitk.Image, idxs: NDArray, expected_points: NDArray
) -> None:
    points = idxs_to_physical_points(image, idxs)
    assert isinstance(points, np.ndarray)
    np.testing.assert_array_almost_equal(points, expected_points)
