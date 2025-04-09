import SimpleITK as sitk

from imgtools.datasets import example_data


def test_data_images() -> None:
    images = example_data()

    assert "duck" in images
    assert "mask" in images

    duck_image = images["duck"]
    mask_image = images["mask"]

    assert isinstance(duck_image, sitk.Image)
    assert isinstance(mask_image, sitk.Image)

    assert duck_image.GetSize() == mask_image.GetSize()
