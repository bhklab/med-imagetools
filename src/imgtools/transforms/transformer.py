from copy import deepcopy
from dataclasses import dataclass
from typing import List

from SimpleITK import Image

from imgtools.logging import logger
from imgtools.transforms import (
    BaseTransform,
    IntensityTransform,
    SpatialTransform,
)


@dataclass
class Transformer:
    transforms: List[BaseTransform]

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

    def __call__(self, images: List[Image]) -> List[Image]:
        """Apply transforms to images."""
        new_images: list[Image] = []

        # handle reference image first
        ref_image: Image = deepcopy(images[0])
        for n, transform in enumerate(self.transforms, start=1):
            if isinstance(transform, (SpatialTransform, IntensityTransform)):
                try:
                    ref_image = transform(ref_image)
                except Exception as e:
                    msg = f"Error applying transform {n}: {transform}."
                    logger.exception(msg)
                    raise ValueError(msg) from e

        # apply all other transforms
        for image in images[1:]:
            new_image: Image = deepcopy(image)
            for transform in self.transforms:
                if isinstance(transform, SpatialTransform):
                    new_image = transform(new_image, ref=ref_image)

            new_images.append(new_image)

        return new_images
