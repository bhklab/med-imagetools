from copy import deepcopy
from dataclasses import dataclass
from typing import List

from imgtools.modalities import Scan, Segmentation, Dose, PET

from imgtools.loggers import logger
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
    
    def _apply_transforms(self, image: Scan | Dose | PET | Segmentation, 
            ref: Scan | Dose | PET | Segmentation | None = None) -> Scan | Dose | PET | Segmentation:
        """Apply transforms to an image."""
        metadata = image.metadata
        new_image: Scan | Dose | PET | Segmentation = image
        for n, transform in enumerate(self.transforms, start=1):
            try:
                if isinstance(transform, SpatialTransform):
                    new_image = transform(new_image, ref=ref) # this is still problematic if the SpatialTransform doesn't have `ref` kwarg
                # doesn't apply intensity transform to non-reference images
                elif isinstance(transform, IntensityTransform) and ref is None:
                    new_image = transform(new_image)
                else:
                    raise ValueError(f"Invalid transform type: {type(transform)}")
            except Exception as e:
                msg = f"Error applying transform {n}: {transform}."
                logger.exception(msg)
                raise ValueError(msg) from e

        return type(image)(new_image, metadata)

    def __call__(self, images: List[Scan | Segmentation | Dose | PET]) -> List[Scan | Segmentation | Dose | PET]:  
        """Apply transforms to images."""
        # handle reference image first
        new_images = [self._apply_transforms(images[0])]
        
        # apply all other transforms
        for image in images[1:]:
            new_image: Scan | Segmentation | Dose | PET = image
            new_images.append(self._apply_transforms(new_image, ref=images[0]))

        return new_images

def main():
    # generate a blank sitk image
    import SimpleITK as sitk
    from imgtools.transforms import Resample

    image = sitk.Image(100, 100, 100, sitk.sitkUInt16) 
    image.SetOrigin((0, 0, 0))
    image.SetSpacing((1, 1, 1))
    image.SetDirection((1, 0, 0, 0, 1, 0, 0, 0, 1))

    # create a blank scan object
    scan = Scan(image, {})

    # create a blank segmentation object
    seg = Segmentation(image, {})

    # create a blank dose object
    dose = Dose(image, {}, 1.0)

    # create a blank pet object
    pet = PET(image, {}, factor=1.0, values_assumed=False, image_type="SUV")

    transforms = [Resample(spacing=(2, 2, 2))]
    transformer = Transformer(transforms)
    transformed_scan = transformer([scan, scan, scan])
    print(transformed_scan)


if __name__ == "__main__":
    main()