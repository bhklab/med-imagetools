"""
Combination of imgtools.ops.functional.image_statistics and pyradiomics general info
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import SimpleITK as sitk

from imgtools.coretypes import Coordinate3D, RegionBox, Size3D, Spacing3D


@dataclass(frozen=True, slots=True)
class ImageData:
    """Class for representing image data (e.g., CT, MRI)."""

    hash: str
    spacing: Spacing3D
    size: Size3D
    dimensions: int
    minimum: float
    maximum: float
    sum: float
    mean: float
    variance: float
    standard_deviation: float

    @classmethod
    def from_image(cls, image: sitk.Image) -> ImageData:
        """Create an instance from a SimpleITK image."""
        # Compute statistics using SimpleITK
        filter_ = sitk.StatisticsImageFilter()
        filter_.Execute(image)

        return cls(
            hash=sitk.Hash(image),
            spacing=Spacing3D(*image.GetSpacing()),
            size=Size3D(*image.GetSize()),
            dimensions=image.GetDimension(),
            minimum=filter_.GetMinimum(),
            maximum=filter_.GetMaximum(),
            sum=filter_.GetSum(),
            mean=filter_.GetMean(),
            variance=filter_.GetVariance(),
            standard_deviation=filter_.GetSigma(),
        )


@dataclass(frozen=True, slots=True)
class MaskData:
    """Class for representing mask data and associated ROI statistics."""

    hash: str
    label: int
    spacing: Spacing3D
    size: Size3D
    dimensions: int
    minimum: float
    maximum: float
    sum: float
    mean: float
    variance: float
    standard_deviation: float
    voxel_count: int
    volume_count: int
    bbox: RegionBox
    centroid_index: Coordinate3D

    @classmethod
    def from_image_and_mask(
        cls, image: sitk.Image, mask: sitk.Image, label: int
    ) -> "MaskData":
        """Create an instance for mask data and associated statistics."""

        # Compute shape-related properties
        label_stats = sitk.LabelShapeStatisticsImageFilter()
        label_stats.Execute(mask)
        bbox = RegionBox.from_mask_bbox(mask)

        centroid_coordinates = label_stats.GetCentroid(label)
        centroid_index = mask.TransformPhysicalPointToIndex(
            centroid_coordinates
        )
        # Count connected components
        label_map = sitk.BinaryThreshold(
            mask, lowerThreshold=label, upperThreshold=label
        )
        cc_filter = sitk.ConnectedComponentImageFilter()
        cc_filter.FullyConnectedOn()
        cc_filter.Execute(label_map)
        volume_count = cc_filter.GetObjectCount()


        binary_mask = sitk.BinaryThreshold(
            mask,
            lowerThreshold=label,
            upperThreshold=label,
            insideValue=1,
            outsideValue=0,
        )

        masked_image = sitk.Mask(image, binary_mask)
        # Compute statistics using SimpleITK
        # Extract statistics only for the region of interest (non-zero pixels in the mask)
        # filter_ = sitk.StatisticsImageFilter()
        # filter_.Execute(masked_image)

        # Calculate statistics over non-zero regions only
        filter_ = sitk.StatisticsImageFilter()
        filter_.Execute(
            masked_image * sitk.Cast(binary_mask, pixelID=image.GetPixelID())
        )

        return cls(
            hash=sitk.Hash(mask),
            label=label,
            spacing=Spacing3D(*mask.GetSpacing()),
            size=Size3D(*mask.GetSize()),
            dimensions=mask.GetDimension(),
            voxel_count=label_stats.GetNumberOfPixels(label),
            volume_count=volume_count,
            bbox=bbox,
            centroid_index=Coordinate3D(*centroid_index),
            minimum=filter_.GetMinimum(),
            maximum=filter_.GetMaximum(),
            sum=filter_.GetSum(),
            mean=filter_.GetMean(),
            variance=filter_.GetVariance(),
            standard_deviation=filter_.GetSigma(),
        )


def main() -> None:
    from rich import print  # noqa
    import time
    from dataclasses import asdict
    from imgtools.datasets.examples import data_images

    img, mask = data_images()["duck"], data_images()["mask"]

    img_data = ImageData.from_image(img)
    mask_data = MaskData.from_image_and_mask(mask, mask, 1)

    print(img_data)
    print(mask_data)
    start = time.time()
    img = sitk.ReadImage(
        "/home/jermiah/bhklab/radiomics/readii-negative-controls/rawdata/RADCURE/images/niftis/SubjectID-7_RADCURE-2639/CT_79752_original.nii.gz"
    )
    mask = sitk.ReadImage(
        "/home/jermiah/bhklab/radiomics/readii-negative-controls/rawdata/RADCURE/images/niftis/SubjectID-7_RADCURE-2639/RTSTRUCT_49024_GTV.nii.gz"
    )
    end_reading = time.time()
    read_time = end_reading - start
    start = time.time()
    img_data = ImageData.from_image(img)
    mask_data = MaskData.from_image_and_mask(mask, mask, 1)
    end = time.time()
    print(img_data)
    print(mask_data)
    print(f"Reading time: {read_time}")
    print(f"Processing time: {end - start}")

    print("Image data:")
    print(asdict(img_data))

    print("Mask data:")
    print(asdict(mask_data))


if __name__ == "__main__":
    main()
