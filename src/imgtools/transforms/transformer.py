from copy import copy
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
        
        # save original image class type + attributes
        img_cls = type(image)
        attrs = image.__dict__.copy()
        del attrs["this"]
        
        for n, transform in enumerate(self.transforms, start=1):
            try:
                if isinstance(transform, SpatialTransform):
                    image = transform(image, ref=ref) # this is still problematic if the SpatialTransform doesn't have `ref` kwarg
                # doesn't apply intensity transform to non-reference images
                elif isinstance(transform, IntensityTransform) and ref is None:
                    image = transform(image)
                else:
                    raise ValueError(f"Invalid transform type: {type(transform)}")
            except Exception as e:
                msg = f"Error applying transform {n}: {transform}."
                logger.exception(msg)
                raise ValueError(msg) from e
        
        # restore original attributes
        obj = img_cls(image, attrs.pop("metadata"))
        for k, v in attrs.items():
            setattr(obj, k, v)
        
        return obj

    def __call__(self, images: List[Scan | Segmentation | Dose | PET]) -> List[Scan | Segmentation | Dose | PET]:  
        """Apply transforms to images."""
        # handle reference image first
        new_images = [self._apply_transforms(images[0])]
        
        # apply all other transforms
        for image in images[1:]:
            new_image: Scan | Segmentation | Dose | PET = image
            new_images.append(self._apply_transforms(new_image, ref=new_images[0]))

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
    dose = Dose(image, {})

    # create a blank pet object
    # pet = PET(image, {}, factor=1.0, values_assumed=False, image_type="SUV")

    transforms = [Resample(spacing=(2, 2, 2))]
    transformer = Transformer(transforms)
    transformed_scan = transformer([scan, seg, dose])
    print(transformed_scan[0].GetSpacing())


if __name__ == "__main__":
    main()