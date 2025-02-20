from __future__ import annotations

from dataclasses import dataclass

import SimpleITK as sitk

from imgtools.coretypes import Coordinate3D, RegionBox, Size3D, Spacing3D


@dataclass(frozen=True, slots=True)
class ImageData:
    """
    Class for representing image data (e.g., CT, MRI).

    Attributes
    ----------
    hash : str
        Unique hash of the image.
    spacing : Spacing3D
        Spacing of the image in each dimension.
    size : Size3D
        Size of the image in each dimension.
    dimensions : int
        Number of dimensions of the image.
    min : float
        Minimum intensity value in the image.
    max : float
        Maximum intensity value in the image.
    sum : float
        Sum of all intensity values in the image.
    mean : float
        Mean intensity value in the image.
    variance : float
        Variance of intensity values in the image.
    std : float
        Standard deviation of intensity values in the image.
    """

    hash: str
    spacing: Spacing3D
    size: Size3D
    dimensions: int
    max: float
    min: float
    mean: float
    std: float
    variance: float
    sum: float

    @classmethod
    def from_image(cls, image: sitk.Image) -> ImageData:
        """
        Create an instance from a SimpleITK image.

        Parameters
        ----------
        image : sitk.Image
            The SimpleITK image from which to compute statistics.

        Returns
        -------
        ImageData
            An instance of ImageData containing computed statistics.
        """
        # Compute statistics using SimpleITK
        filter_ = sitk.StatisticsImageFilter()
        filter_.Execute(image)

        return cls(
            hash=sitk.Hash(image),
            spacing=Spacing3D(*image.GetSpacing()),
            size=Size3D(*image.GetSize()),
            dimensions=image.GetDimension(),
            min=filter_.GetMinimum(),
            max=filter_.GetMaximum(),
            sum=filter_.GetSum(),
            mean=filter_.GetMean(),
            variance=filter_.GetVariance(),
            std=filter_.GetSigma(),
        )


@dataclass(frozen=True, slots=True)
class MaskData:
    """
    Class for representing mask data and associated statistics.

    Attributes
    ----------
    hash : str
        Unique hash of the mask.
    spacing : Spacing3D
        Spacing of the mask in each dimension.
    size : Size3D
        Size of the mask in each dimension.
    dimensions : int
        Number of dimensions of the mask.
    masked_max : int
        Maximum intensity value within the masked region.
    masked_min : int
        Minimum intensity value within the masked region.
    masked_mean : float
        Mean intensity value within the masked region.
    masked_std : float
        Standard deviation of intensity values within the masked region.
    masked_variance : float
        Variance of intensity values within the masked region.
    masked_sum : float
        Sum of all intensity values within the masked region.
    num_labels : int
        Number of labels in the mask.
    label : int
        Label value for the mask.
    perimeter : float
        Perimeter of the labeled region.
    touching_border : bool
        Whether the labeled region touches the border of the mask.
    voxel_count : int
        Number of voxels in the labeled region.
    volume_count : int
        Number of connected components in the labeled region.
    bbox : RegionBox
        Bounding box of the labeled region.
    centroid_index : Coordinate3D
        Centroid index of the labeled region.
    """

    hash: str
    spacing: Spacing3D
    size: Size3D
    dimensions: int
    masked_max: int
    masked_min: int
    masked_mean: float
    masked_std: float
    masked_variance: float
    masked_sum: float
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
        """
        Create an instance for mask data and associated statistics.

        Parameters
        ----------
        image : sitk.Image
            The SimpleITK image associated with the mask.
        mask : sitk.Image
            The SimpleITK mask image.
        label : int
            The label value to compute statistics for.

        Returns
        -------
        MaskData
            An instance of MaskData containing computed statistics.
        """
        # Compute shape-related properties
        label_stats = sitk.LabelShapeStatisticsImageFilter()
        label_stats.ComputePerimeterOn()
        label_stats.Execute(mask)

        centroid_coordinates = label_stats.GetCentroid(label)
        centroid_index = mask.TransformPhysicalPointToIndex(
            centroid_coordinates
        )

        masked_image = sitk.Mask(image, mask == label)
        masked_array = sitk.GetArrayFromImage(masked_image)
        if (masked_array_nonzero := masked_array[masked_array != 0]) is None:
            msg = f"No non-zero values found in masked region with {label=}."
            raise ValueError(msg)

        # Count connected components
        label_map = sitk.BinaryThreshold(
            mask, lowerThreshold=label, upperThreshold=label
        )
        cc_filter = sitk.ConnectedComponentImageFilter()
        cc_filter.FullyConnectedOn()
        cc_filter.Execute(label_map)

        return cls(
            hash=sitk.Hash(mask),
            spacing=Spacing3D(*mask.GetSpacing()),
            size=Size3D(*mask.GetSize()),
            dimensions=mask.GetDimension(),
            num_labels=label_stats.GetNumberOfLabels(),
            label=label,
            masked_max=int(masked_array_nonzero.max()),
            masked_min=int(masked_array_nonzero.min()),
            masked_mean=float(masked_array_nonzero.mean()),
            masked_std=float(masked_array_nonzero.std()),
            masked_variance=float(masked_array_nonzero.var()),
            masked_sum=masked_array_nonzero.sum(),
            voxel_count=label_stats.GetNumberOfPixels(label),
            volume_count=cc_filter.GetObjectCount(),
            bbox=RegionBox.from_mask_bbox(mask),
            centroid_index=Coordinate3D(*centroid_index),
            perimeter=round(label_stats.GetPerimeter(label), 5),
            touching_border=label_stats.GetPerimeterOnBorder(label) > 0,
        )


def main() -> None:
    from rich import print  # noqa
    from imgtools.ops import ImageAutoInput
    # from dataclasses import asdict
    from imgtools.coretypes import RegionBox

    inputter = ImageAutoInput(
        "devnotes/notebooks/dicoms", modalities="CT,RTSTRUCT"
    )
    subjectids = list(inputter._loader.keys())

    scan, rtss = inputter(subjectids[0])
    img = scan.image

    mask_rtss = rtss.to_segmentation(
        img, {"GTV": "GTV.*"}
    )  # because of the way the we handle dictionaries, this will have 2 volumes in the same mask

    img_data = ImageData.from_image(img)
    print("*" * 80)
    print("*" * 80)

    print(img_data)
    # print('[red]printed as json: [/red]')
    # print(asdict(img_data))

    print("*" * 80)
    print("*" * 80)
    mask = mask_rtss.get_label(1)
    mask_data = MaskData.from_image_and_mask(img, mask, 1)
    print(mask_data)
    # print("*" * 80)
    # print(asdict(mask_data))

    cropped_image, cropped_mask = RegionBox.from_mask_bbox(
        mask
    ).crop_image_and_mask(img, mask)

    cropped_mask_data = MaskData.from_image_and_mask(
        cropped_image, cropped_mask, 1
    )
    print("[bold green]\nmask_stats(cropped to exactly bbox)")
    print(cropped_mask_data)


if __name__ == "__main__":
    main()
