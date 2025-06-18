from dataclasses import dataclass
from typing import Generic, Sequence, TypeVar

import SimpleITK as sitk

from imgtools.coretypes.base_masks import VectorMask
from imgtools.coretypes.base_medimage import MedImage
from imgtools.loggers import logger
from imgtools.transforms import (
    BaseTransform,
    IntensityTransform,
    SpatialTransform,
)

# Define TypeVars for the different image types
T_MedImage = TypeVar("T_MedImage", bound=MedImage)


@dataclass
class Transformer(Generic[T_MedImage]):
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

    def _apply_transforms(
        self,
        image: T_MedImage,
        ref: MedImage | None = None,
    ) -> T_MedImage:
        """Apply transforms to an image, preserving its type.

        Parameters
        ----------
        image : T_MedImage
            The image to transform, can be any subclass of MedImage
        ref : MedImage, optional
            For some transforms, a reference image can be used for
            transformation. This is typically used for spatial transforms
            like Resample.

        Returns
        -------
        T_MedImage
            The transformed image, with the same type as the input
        """
        # save original image class type + attributes
        img_cls = type(image)
        # Store the metadata (all MedImage subclasses should have this)
        metadata = getattr(image, "metadata", None)

        # Apply all transforms in sequence
        transformed_image = image
        for n, transform in enumerate(self.transforms, start=1):
            try:
                if (
                    isinstance(transform, SpatialTransform)
                    and transform.supports_reference()
                ):
                    transformed_image = transform(transformed_image, ref)
                elif isinstance(
                    transform, (IntensityTransform, SpatialTransform)
                ):
                    transformed_image = transform(transformed_image)
                else:
                    msg = f"Invalid transform type: {type(transform)}"
                    raise ValueError(msg)
            except Exception as e:
                msg = f"Error applying transform {n}: {transform}."
                logger.exception(msg)
                raise ValueError(msg) from e

        # Restore original attributes based on the type
        try:
            if isinstance(image, VectorMask):
                roi_mapping = getattr(image, "roi_mapping", None)
                result = img_cls(  # type: ignore
                    transformed_image,
                    roi_mapping=roi_mapping,
                    metadata=metadata,
                )
                return result
                # return cast(T_MedImage, result)
            elif isinstance(image, MedImage):
                result = img_cls(  # type: ignore
                    transformed_image,
                    metadata=metadata,
                )
                return result
            else:
                # For plain sitk.Image, just return the transformed image
                return result
        except Exception as e:
            msg = f"Error restoring original attributes for image: {image}."
            logger.exception(msg)
            raise ValueError(msg) from e

    def __call__(self, images: Sequence[T_MedImage]) -> Sequence[T_MedImage]:
        """Apply transforms to a sequence of images.

        Parameters
        ----------
        images : Sequence[T_MedImage]
            A sequence of images to transform

        Returns
        -------
        Sequence[T_MedImage]
            The transformed images, with the same types as the inputs
        """
        # Initialize new image list
        new_images: list[T_MedImage] = [self._apply_transforms(images[0])]

        # Process each image
        for image in images[1:]:
            # Apply transforms and maintain type
            new_images.append(self._apply_transforms(image, ref=new_images[0]))

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

    transforms: list[BaseTransform] = []
    transforms = [
        Resample(spacing=(2, 2, 2)),
        WindowIntensity(window=400.0, level=0.0),
    ]
    transformer: Transformer[MedImage]
    transformer = Transformer(transforms)
    transformed_scan = transformer([scan])

    min_intensity, max_intensity = sitk.MinimumMaximum(
        image=transformed_scan[0]
    )
    print(f"Transformed min intensity: {min_intensity}")  # noqa: T201
    print(f"Transformed max intensity: {max_intensity}")  # noqa: T201


if __name__ == "__main__":
    main()
