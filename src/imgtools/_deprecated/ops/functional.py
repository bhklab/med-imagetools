from collections import namedtuple
from typing import List, Optional, Sequence, Tuple

import numpy as np
import SimpleITK as sitk

from imgtools._deprecated import Segmentation

# def constant_pad(image, size, cval=0.):
#     if isinstance(size, int):
#         size_lower = size_upper = [size for _ in image.GetSize()]
#     elif isinstance(size, (tuple, list, np.ndarray)):
#         if isinstance(size[0], int):
#             size_lower = size_upper = size
#         elif isinstance(size[0], (tuple, list, np.ndarray)):
#             size_lower = [s[0] for s in size]
#             size_upper = [s[1] for s in size]
#     else:
#         raise ValueError(
#             f"Size must be either int, sequence of int or sequence of sequences of ints, got {size}."
#         )
#     return sitk.ConstantPad(image, size_lower, size_upper, cval)

# def centre_on_point(image, centre):
#     pass

# def resize_by_cropping_or_padding(image, size, centre=None, cval=0.):
#     original_size = np.array(image.GetSize())
#     size = np.asarray(size)
#     centre = np.asarray(centre) if centre is not None else original_size / 2 # XXX is there any benefit to not using floor div here?

#     crop_dims = np.where(size < original_size)


def bounding_box(
    mask: sitk.Image, label: int = 1
) -> Tuple[Tuple | np.ndarray, Tuple | np.ndarray]:
    """Find the axis-aligned bounding box of a region descriibed by a
    segmentation mask.

    Parameters
    ----------
    mask
        Segmentation mask describing the region of interest. Can be an image of
        type unsigned int representing a label map or `segmentation.Segmentation`.

    label, optional
        Label to use when computing bounding box if segmentation mask contains
        more than 1 labelled region.

    Returns
    -------
    tuple of tuples
        The bounding box location and size. The first tuple gives the
        coordinates of the corner closest to the origin and the second
        gives the size in pixels along each dimension.

    Examples
    --------
    >>> box_coords = bounding_box(mask)
    >>> print(box_coords)
    ((201, 111, 79), (115, 103, 30))
    """

    if isinstance(mask, Segmentation):
        seg = Segmentation(mask)
        mask = seg.get_label(label=label, relabel=True)

    filter_ = sitk.LabelShapeStatisticsImageFilter()
    filter_.Execute(mask)
    bbox = filter_.GetBoundingBox(label)
    location = bbox[: len(bbox) // 2]
    size = bbox[len(bbox) // 2 :]
    return location, size


def centroid(
    mask: sitk.Image, label: int = 1, world_coordinates: bool = False
) -> tuple:
    """Find the centroid of a labelled region specified by a segmentation mask.

    Parameters
    ----------
    mask
        Segmentation mask describing the region of interest. Can be an image of
        type unsigned int representing a label map or `segmentation.Segmentation`.

    label, optional
        Label to use when computing the centroid if segmentation mask contains
        more than 1 labelled region.

    world_coordinates, optional
        If True, return centroid in world coordinates, otherwise in image
        (voxel) coordinates (default).

    Returns
    -------
    tuple
        The centroid coordinates.

    Examples
    --------
    >>> centre_coords = centroid(mask)
    >>> print(centre_coords)
    (259, 155, 88)
    """

    if isinstance(mask, Segmentation):
        seg = Segmentation(mask)
        mask = seg.get_label(label=label, relabel=True)

    filter_ = sitk.LabelShapeStatisticsImageFilter()
    filter_.Execute(mask)
    centroid_coords = filter_.GetCentroid(label)
    if not world_coordinates:
        centroid_coords = mask.TransformPhysicalPointToIndex(centroid_coords)
    return centroid_coords


def crop_to_mask_bounding_box(
    image: sitk.Image,
    mask: sitk.Image,
    margin: int | List[int] | np.ndarray = 0,
    label: int = 1,
) -> Tuple[sitk.Image, sitk.Image, List[float]]:
    """Crop the image using the bounding box of a region of interest specified
    by a segmentation mask.

    Parameters
    ----------
    image
        The image to crop.

    mask
        Segmentation mask describing the region of interest. Can be an image of
        type unsigned int representing a label map or `segmentation.Segmentation`.

    margin, optional
        A margin that will be added to each dimension when cropping. If int,
        add the same margin to each dimension. A sequence of ints can also be
        passed to specify the margin separately along each dimension.

    label, optional
        Label to use when computing the centroid if segmentation mask contains
        more than 1 labelled region.

    Returns
    -------
    tuple of sitk.Image
        The cropped image, the cropped mask, and the crop centre.

    Examples
    --------
    >>> cropped_image, cropped_mask, crop_centre = (
    ...     crop_to_mask_bounding_box(
    ...         example_image, mask
    ...     )
    ... )
    """

    if isinstance(mask, Segmentation):
        seg = Segmentation(mask)
        mask = seg.get_label(label=label, relabel=True)

    if isinstance(margin, Sequence):
        margin = np.asarray(margin)

    bbox_location, bbox_size = bounding_box(mask, label=label)
    bbox_location, bbox_size = np.array(bbox_location), np.array(bbox_size)
    crop_size = bbox_size + margin * 2
    crop_centre = list(bbox_location - margin + crop_size / 2)

    image = crop(image, crop_centre, crop_size)
    mask = crop(mask, crop_centre, crop_size)

    return image, mask, crop_centre




ImageStatistics = namedtuple(
    "ImageStatistics",
    [
        "minimum",
        "maximum",
        "sum",
        "mean",
        "variance",
        "standard_deviation",
    ],
)


def image_statistics(
    image: sitk.Image, mask: sitk.Image | None = None, label: int = 1
) -> ImageStatistics:
    """Compute the intensity statistics of an image.

    Returns the minimum, maximum, sum, mean, variance and standard deviation
    of image intensities.
    This function also supports computing the statistics in a specific
    region of interest if `mask` and `label` are passed.

    Parameters
    ----------
    image
        The image used to compute the statistics.

    mask, optional
        Segmentation mask specifying a region of interest used in computation.
        Can be an image of type unsigned int representing a label map or
        `segmentation.Segmentation`. Only voxels falling within the ROI will
        be considered. If None, use the whole image.

    label, optional
        Label to use when computing the statistics if segmentation mask contains
        more than 1 labelled region.

    Returns
    -------
    ImageStatistics, collections.namedtuple
        The computed intensity statistics in the image or region.
    """

    filter_: sitk.LabelStatisticsImageFilter | sitk.StatisticsImageFilter
    if mask is not None:
        if isinstance(mask, Segmentation):
            seg = Segmentation(mask)
            mask = seg.get_label(label=label, relabel=True)

        filter_ = sitk.LabelStatisticsImageFilter()
        filter_.Execute(image, mask)
        result = ImageStatistics(
            minimum=filter_.GetMinimum(label),
            maximum=filter_.GetMaximum(label),
            sum=filter_.GetSum(label),
            mean=filter_.GetMean(label),
            variance=filter_.GetVariance(label),
            standard_deviation=filter_.GetSigma(label),
        )
    else:
        filter_ = sitk.StatisticsImageFilter()
        filter_.Execute(image)
        result = ImageStatistics(
            minimum=filter_.GetMinimum(),
            maximum=filter_.GetMaximum(),
            sum=filter_.GetSum(),
            mean=filter_.GetMean(),
            variance=filter_.GetVariance(),
            standard_deviation=filter_.GetSigma(),
        )

    return result


