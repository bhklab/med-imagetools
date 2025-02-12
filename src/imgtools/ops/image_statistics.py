from __future__ import annotations

from dataclasses import dataclass

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
    spacing: Spacing3D
    size: Size3D
    dimensions: int
    num_labels: int
    label: int
    perimeter: float
    touching_border: bool
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
        label_stats.ComputePerimeterOn()
        label_stats.Execute(mask)
        bbox = RegionBox.from_mask_bbox(mask)

        label_perimeter = round(label_stats.GetPerimeter(label), 5)
        label_touching_border = label_stats.GetPerimeterOnBorder(label) > 0

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
            num_labels=label_stats.GetNumberOfLabels(),
            perimeter=label_perimeter,
            touching_border=label_touching_border,
        )


def main() -> None:
    from rich import print  # noqa
    from dataclasses import asdict
    from imgtools.ops import ImageAutoInput
    from imgtools.datasets.examples import data_images
    from imgtools.coretypes import RegionBox

    # img, mask = data_images()["duck"], data_images()["mask"]

    # img_data = ImageData.from_image(img)
    # mask_data = MaskData.from_image_and_mask(mask, mask, 1)

    # print(img_data)
    # print(mask_data)
    # print("scan_stats")
    # print(asdict(img_data))

    # print("mask_stats")
    # print(asdict(mask_data))
    img = sitk.ReadImage(
        "/home/jermiah/bhklab/radiomics/readii-negative-controls/rawdata/RADCURE/images/niftis/SubjectID-7_RADCURE-2639/CT_79752_original.nii.gz"
    )
    mask = sitk.ReadImage(
        "/home/jermiah/bhklab/radiomics/readii-negative-controls/rawdata/RADCURE/images/niftis/SubjectID-7_RADCURE-2639/RTSTRUCT_49024_GTV.nii.gz"
    )

    inputter = ImageAutoInput(
        "devnotes/notebooks/dicoms", modalities="CT,RTSTRUCT"
    )
    subjectids = list(inputter._loader.keys())

    scan, rtss = inputter(subjectids[0])
    img = scan.image
    # print(rtss.roi_names)
    mask_rtss = rtss.to_segmentation(img, {"GTV": "GTV.*"})
    # print(mask_rtss.roi_indices)
    mask = mask_rtss.get_label(1)

    img_data = ImageData.from_image(img)
    mask_data = MaskData.from_image_and_mask(mask, mask, 1)
    print("scan_stats")
    print(asdict(img_data))

    print("mask_stats")
    print(asdict(mask_data))

    cropped_mask = RegionBox.from_mask_bbox(mask).crop_image(mask)
    cropped_mask_data = MaskData.from_image_and_mask(
        cropped_mask, cropped_mask, 1
    )
    print("mask_stats(cropped to exactly bbox)")
    print(asdict(cropped_mask_data))


if __name__ == "__main__":
    main()
