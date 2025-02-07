import pytest
from rich import print as rprint
import SimpleITK as sitk
from imgtools.coretypes import RegionBox, Coordinate3D, Size3D, BoxPadMethod
from imgtools.coretypes.box import BoundingBoxOutsideImageError
from imgtools.datasets import example_data
# Simple tests
def test_regionbox_initialization():
    min_coord = Coordinate3D(0, 0, 0)
    max_coord = Coordinate3D(10, 10, 10)
    box = RegionBox(min_coord, max_coord)
    assert box.min == min_coord
    assert box.max == max_coord
    assert box.size == Size3D(10, 10, 10)

def test_regionbox_invalid_initialization():
    min_coord = Coordinate3D(10, 10, 10)
    max_coord = Coordinate3D(0, 0, 0)
    with pytest.raises(ValueError):
        RegionBox(min_coord, max_coord)

def test_regionbox_from_tuple():
    box = RegionBox.from_tuple((0, 0, 0), (10, 10, 10))
    assert box.min == Coordinate3D(0, 0, 0)
    assert box.max == Coordinate3D(10, 10, 10)
    assert box.size == Size3D(10, 10, 10)

def test_regionbox_pad_symmetric():
    box = RegionBox(Coordinate3D(5, 5, 5), Coordinate3D(10, 10, 10))
    padded_box = box.pad(5)
    assert padded_box.min == Coordinate3D(0, 0, 0)
    assert padded_box.max == Coordinate3D(15, 15, 15)
    assert padded_box.size == Size3D(15, 15, 15)

def test_regionbox_pad_end():
    box = RegionBox(Coordinate3D(5, 5, 5), Coordinate3D(10, 10, 10))
    padded_box = box.pad(5, method=BoxPadMethod.END)
    assert padded_box.min == Coordinate3D(5, 5, 5)
    assert padded_box.max == Coordinate3D(15, 15, 15)
    assert padded_box.size == Size3D(10, 10, 10)

def test_regionbox_expand_to_cube():
    box = RegionBox(Coordinate3D(5, 5, 5), Coordinate3D(10, 10, 10))
    cube_box = box.expand_to_cube(15)
    assert cube_box.size == Size3D(15, 15, 15)

def test_regionbox_expand_to_min_size():
    box = RegionBox(Coordinate3D(5, 5, 5), Coordinate3D(15, 15, 15))
    min_size_box = box.expand_to_min_size(20)
    assert min_size_box.size == Size3D(20, 20, 20)

def test_regionbox_crop_image():
    image = sitk.Image(100, 100, 100, sitk.sitkInt16)
    box = RegionBox(Coordinate3D(10, 10, 10), Coordinate3D(20, 20, 20))
    cropped_image = box.crop_image(image)
    assert cropped_image.GetSize() == (10, 10, 10)

def test_regionbox_crop_image_outside():
    image = sitk.Image(100, 100, 100, sitk.sitkInt16)
    box = RegionBox(Coordinate3D(90, 90, 90), Coordinate3D(110, 110, 110))
    with pytest.raises(BoundingBoxOutsideImageError):
        box.crop_image(image)

def test_regionbox_crop_image_and_mask():
    image = sitk.Image(100, 100, 100, sitk.sitkInt16)
    mask = sitk.Image(100, 100, 100, sitk.sitkUInt8)
    box = RegionBox(Coordinate3D(10, 10, 10), Coordinate3D(20, 20, 20))
    cropped_image, cropped_mask = box.crop_image_and_mask(image, mask)
    assert cropped_image.GetSize() == (10, 10, 10)
    assert cropped_mask.GetSize() == (10, 10, 10)

# Edge cases

def test_regionbox_from_centroid_odd_cube():

    mask = example_data()['mask']
    rprint("testing odd cube")
    bbox = RegionBox.from_mask_centroid(mask, 1, 0)
    rprint(bbox)

    rprint("expanding to size 5")

    bbox = RegionBox.from_mask_centroid(mask, 1, 5)
    rprint(bbox)

def test_bbox_cubed()->None:
    mask = example_data()['mask']
    bbox = RegionBox.from_mask_bbox(mask, 1)
    rprint(bbox)
    bbox = RegionBox.from_mask_bbox(mask, 1).expand_to_cube()
    rprint(bbox)