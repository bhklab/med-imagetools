import pytest
import SimpleITK as sitk
from rich import print as rprint

from imgtools.coretypes import BoxPadMethod, Coordinate3D, RegionBox, Size3D
from imgtools.coretypes.box import BoundingBoxOutsideImageError
from imgtools.datasets import example_data


# Simple tests
def test_regionbox_initialization() -> None:
    min_coord = Coordinate3D(0, 0, 0)
    max_coord = Coordinate3D(10, 10, 10)
    box = RegionBox(min_coord, max_coord)
    assert box.min == min_coord
    assert box.max == max_coord
    assert box.size == Size3D(10, 10, 10)


def test_regionbox_invalid_initialization() -> None:
    min_coord = Coordinate3D(10, 10, 10)
    max_coord = Coordinate3D(0, 0, 0)
    with pytest.raises(ValueError):
        RegionBox(min_coord, max_coord)


def test_regionbox_from_tuple() -> None:
    box = RegionBox.from_tuple((0, 0, 0), (10, 10, 10))
    assert box.min == Coordinate3D(0, 0, 0)
    assert box.max == Coordinate3D(10, 10, 10)
    assert box.size == Size3D(10, 10, 10)


def test_regionbox_pad_symmetric() -> None:
    box = RegionBox(Coordinate3D(5, 5, 5), Coordinate3D(10, 10, 10))
    padded_box = box.pad(5)
    assert padded_box.min == Coordinate3D(0, 0, 0)
    assert padded_box.max == Coordinate3D(15, 15, 15)
    assert padded_box.size == Size3D(15, 15, 15)


def test_regionbox_pad_end() -> None:
    box = RegionBox(Coordinate3D(5, 5, 5), Coordinate3D(10, 10, 10))
    padded_box = box.pad(5, method=BoxPadMethod.END)
    assert padded_box.min == Coordinate3D(5, 5, 5)
    assert padded_box.max == Coordinate3D(15, 15, 15)
    assert padded_box.size == Size3D(10, 10, 10)


def test_regionbox_expand_to_cube() -> None:
    box = RegionBox(Coordinate3D(5, 5, 5), Coordinate3D(10, 10, 10))
    cube_box = box.expand_to_cube(15)
    assert cube_box.size == Size3D(15, 15, 15)


def test_regionbox_expand_to_min_size() -> None:
    box = RegionBox(Coordinate3D(5, 5, 5), Coordinate3D(15, 15, 15))
    min_size_box = box.expand_to_min_size(20)
    assert min_size_box.size == Size3D(20, 20, 20)


def test_regionbox_crop_image() -> None:
    image = sitk.Image(100, 100, 100, sitk.sitkInt16)
    box = RegionBox(Coordinate3D(10, 10, 10), Coordinate3D(20, 20, 20))
    cropped_image = box.crop_image(image)
    assert cropped_image.GetSize() == (10, 10, 10)


def test_regionbox_crop_image_outside() -> None:
    image = sitk.Image(100, 100, 100, sitk.sitkInt16)
    box = RegionBox(Coordinate3D(90, 90, 90), Coordinate3D(110, 110, 110))
    cropped = box.crop_image(image)

    assert cropped.GetSize() == (20, 20, 20)


def test_regionbox_crop_image_and_mask() -> None:
    image = sitk.Image(100, 100, 100, sitk.sitkInt16)
    mask = sitk.Image(100, 100, 100, sitk.sitkUInt8)
    box = RegionBox(Coordinate3D(10, 10, 10), Coordinate3D(20, 20, 20))
    cropped_image, cropped_mask = box.crop_image_and_mask(image, mask)
    assert cropped_image.GetSize() == (10, 10, 10)
    assert cropped_mask.GetSize() == (10, 10, 10)


# Edge cases


def test_regionbox_from_centroid_odd_cube() -> None:
    mask = example_data()["mask"]
    bbox = RegionBox.from_mask_centroid(mask, 1, 5)
    expected = RegionBox(Coordinate3D(47, 26, 73), Coordinate3D(52, 31, 78))

    assert bbox.min == expected.min
    assert bbox.max == expected.max
    assert bbox.size == expected.size


def test_bbox_cubed() -> None:
    region = RegionBox(Coordinate3D(12, 13, 14), Coordinate3D(21, 23, 25))

    expanded_region = region.expand_to_cube(13)

    expected = RegionBox(Coordinate3D(10, 11, 13), Coordinate3D(23, 24, 26))

    assert expanded_region.min == expected.min
    assert expanded_region.max == expected.max
    assert expanded_region.size == expected.size


def test_adjust_max() -> None:
    region = RegionBox(Coordinate3D(12, 13, 14), Coordinate3D(21, 23, 25))

    # save a copy to compare size after
    region_copy = region.copy()

    image = sitk.Image(20, 20, 20, sitk.sitkInt16)

    region.check_out_of_bounds_coordinates(image=image)

    assert region.size == region_copy.size

    expected_min = Coordinate3D(11, 10, 9)
    expected_max = Coordinate3D(20, 20, 20)

    assert region.min == expected_min
    assert region.max == expected_max


def test_expand_cube_smaller_size() -> None:
    region = RegionBox(Coordinate3D(12, 13, 14), Coordinate3D(200, 23, 25))
    with pytest.raises(ValueError):
        _ = region.expand_to_cube(10)


def test_regionbox_from_mask_bbox() -> None:
    mask = example_data()["mask"]
    bbox = RegionBox.from_mask_bbox(mask)
    expected = RegionBox(Coordinate3D(45, 21, 67), Coordinate3D(55, 38, 84))

    assert bbox.min == expected.min
    assert bbox.max == expected.max
    assert bbox.size == expected.size


def test_regionbox_expand_to_min_size_no_change() -> None:
    box = RegionBox(Coordinate3D(5, 5, 5), Coordinate3D(15, 15, 15))
    min_size_box = box.expand_to_min_size(5)
    assert min_size_box.size == Size3D(10, 10, 10)


def test_regionbox_expand_to_cube_no_change() -> None:
    box = RegionBox(Coordinate3D(5, 5, 5), Coordinate3D(15, 15, 15))
    cube_box = box.expand_to_cube(10)
    assert cube_box.size == Size3D(10, 10, 10)


def test_regionbox_pad_no_change() -> None:
    box = RegionBox(Coordinate3D(5, 5, 5), Coordinate3D(10, 10, 10))
    padded_box = box.pad(0)
    assert padded_box.min == Coordinate3D(5, 5, 5)
    assert padded_box.max == Coordinate3D(10, 10, 10)
    assert padded_box.size == Size3D(5, 5, 5)


def test_regionbox_repr() -> None:
    box = RegionBox(Coordinate3D(5, 5, 5), Coordinate3D(10, 10, 10))
    repr_str = repr(box)
    expected_str = (
        "RegionBox(\n"
        "\tmin=Coordinate3D(x=5, y=5, z=5),\n"
        "\tmax=Coordinate3D(x=10, y=10, z=10)\n"
        "\tsize=Size3D(w=5, h=5, d=5)\n"
        ")"
    )
    assert repr_str == expected_str


def test_regionbox_copy() -> None:
    box = RegionBox(Coordinate3D(5, 5, 5), Coordinate3D(10, 10, 10))
    box_copy = box.copy()
    assert box_copy.min == box.min
    assert box_copy.max == box.max
    assert box_copy.size == box.size


def test_regionbox_adjust_negative_coordinates() -> None:
    min_coord = Coordinate3D(-5, -5, -5)
    max_coord = Coordinate3D(10, 10, 10)
    RegionBox._adjust_negative_coordinates(min_coord, max_coord)
    assert min_coord == Coordinate3D(0, 0, 0)
    assert max_coord == Coordinate3D(15, 15, 15)


def test_regionbox_check_out_of_bounds_coordinates() -> None:
    image = sitk.Image(20, 20, 20, sitk.sitkInt16)
    region = RegionBox(Coordinate3D(12, 13, 14), Coordinate3D(21, 23, 25))
    region.check_out_of_bounds_coordinates(image)
    assert region.min == Coordinate3D(11, 10, 9)
    assert region.max == Coordinate3D(20, 20, 20)
