from dataclasses import dataclass
from typing import List, Sequence

import SimpleITK as sitk

from imgtools.loggers import logger
from imgtools.transforms import (
    BaseTransform,
    IntensityTransform,
    SpatialTransform,
)


@dataclass
class Transformer:
    transforms: Sequence[BaseTransform]

    def __post_init__(self) -> None:
        """Validate transforms."""
        errors: list[str] = []
        for transform in self.transforms:
            if isinstance(transform, BaseTransform):
                continue
            msg = f"Invalid transform type: {type(transform)}. "
            errors.append(msg)
        if errors:
            errmsg = "All transforms must be instances of `BaseTransform`"
            errors.append(errmsg)
            raise ValueError("\n".join(errors))

    def _apply_transforms(self, image: sitk.Image) -> sitk.Image:
        """Apply transforms to an image."""

        # save original image class type + attributes
        img_cls = type(image)
        attrs = image.__dict__.copy()
        del attrs["this"]

        for n, transform in enumerate(self.transforms, start=1):
            try:
                if isinstance(
                    transform, (SpatialTransform, IntensityTransform)
                ):
                    image = transform(image)
                else:
                    msg = f"Invalid transform type: {type(transform)}"
                    raise ValueError(msg)
            except Exception as e:
                msg = f"Error applying transform {n}: {transform}."
                logger.exception(msg)
                raise ValueError(msg) from e

        # restore original attributes
        obj = img_cls(image, attrs.pop("metadata"))
        for k, v in attrs.items():
            setattr(obj, k, v)

        return obj

    def __call__(self, images: List[sitk.Image]) -> List[sitk.Image]:
        """Apply transforms to images."""
        # handle reference image first
        new_images = [self._apply_transforms(images[0])]

        # apply all other transforms
        for image in images[1:]:
            new_image: sitk.Image = image
            new_images.append(self._apply_transforms(new_image))

        return new_images


def main() -> None:
    from rich import print  # noqa

    # generate a blank sitk image
    from imgtools.coretypes.imagetypes import Scan
    from imgtools.transforms import Resample, WindowIntensity

    path = "data/4D-Lung/113_HM10395/CT_Series-00173972"
    scan = Scan.from_dicom(path)
    print(scan)  # noqa: T201

    # get min and max intensity values
    min_intensity, max_intensity = sitk.MinimumMaximum(image=scan)
    print(f"Min intensity: {min_intensity}")  # noqa: T201
    print(f"Max intensity: {max_intensity}")  # noqa: T201

    transforms = [
        Resample(spacing=(2, 2, 2)),
        WindowIntensity(window=400.0, level=0.0),
    ]
    transformer = Transformer(transforms)
    transformed_scan = transformer([scan])

    min_intensity, max_intensity = sitk.MinimumMaximum(
        image=transformed_scan[0]
    )
    print(f"Transformed min intensity: {min_intensity}")  # noqa: T201
    print(f"Transformed max intensity: {max_intensity}")  # noqa: T201


if __name__ == "__main__":
    main()
