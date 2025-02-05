from __future__ import annotations

from functools import wraps
from typing import Any, Callable, List, Optional, Union

import SimpleITK as sitk

from .segmentation import Segmentation


def accepts_segmentations(f: Callable) -> Callable:
    """A decorator that ensures functions can handle `Segmentation` objects correctly.

    If the input image is an instance of `Segmentation`, the decorator preserves
    the ROI indices and raw ROI names in the output.

    This is useful when using functions that process images without losing metadata
    for the Segmentation class.

    Parameters
    ----------
    f : Callable
        The function to wrap, which processes an image.

    Returns
    -------
    Callable
        A wrapped function that preserves `Segmentation` metadata if the input
        is a `Segmentation` object.

    Examples
    --------

    Define a function that processes an image and is decorated with `@accepts_segmentations`:
    >>> @accepts_segmentations
    ... def some_processing_function(
    ...     img,
    ...     *args,
    ...     **kwargs,
    ... ) -> sitk.Image:
            # Perform some operation on the image
    ...     return img
    >>> segmentation = Segmentation(
    ...     image,
    ...     roi_indices={
    ...         "ROI1": 1,
    ...         "ROI2": 2,
    ...     },
    ... )
    >>> result = some_processing_function(segmentation)
    >>> isinstance(
    ...     result,
    ...     Segmentation,
    ... )
    True
    >>> print(result.roi_indices)
    {"ROI1": 1, "ROI2": 2}
    """

    @wraps(f)
    def wrapper(
        img: Union[sitk.Image, Segmentation],
        *args: Any,  # noqa
        **kwargs: Any,  # noqa
    ) -> Union[sitk.Image, Segmentation]:
        result = f(img, *args, **kwargs)
        if isinstance(img, Segmentation):
            result = sitk.Cast(result, sitk.sitkVectorUInt8)
            return Segmentation(
                result,
                roi_indices=img.roi_indices,
                raw_roi_names=img.raw_roi_names,
            )
        return result

    return wrapper


def map_over_labels(
    segmentation: Segmentation,
    f: Callable[[sitk.Image], sitk.Image],
    include_background: bool = False,
    return_segmentation: bool = True,
    **kwargs: Any,  # noqa
) -> Union[List[sitk.Image], Segmentation]:
    """
    Applies a function to each label in a segmentation mask.

    This function iterates over all labels in the segmentation mask, applies
    the provided function to each label individually, and optionally combines
    the results into a new `Segmentation` object.

    Parameters
    ----------
    segmentation : Segmentation
        The segmentation object containing multiple ROI labels.
    f : Callable[[sitk.Image], sitk.Image]
        A function to apply to each label in the segmentation.
    include_background : bool, optional
        If True, includes the background label (label 0) in the operation.
        Default is False.
    return_segmentation : bool, optional
        If True, combines the results into a new `Segmentation` object.
        If False, returns a list of processed labels as `sitk.Image`. Default is True.
    **kwargs : Any
        Additional keyword arguments passed to the function `f`.

    Returns
    -------
    Union[List[sitk.Image], Segmentation]
        A new `Segmentation` object if `return_segmentation` is True,
        otherwise a list of `sitk.Image` objects for each label.

    Examples
    --------
    >>> def threshold(
    ...     label_img,
    ...     threshold=0.5,
    ... ):
    ...     return sitk.BinaryThreshold(
    ...         label_img,
    ...         lowerThreshold=threshold,
    ...     )
    >>> segmentation = Segmentation(
    ...     image,
    ...     roi_indices={
    ...         "ROI1": 1,
    ...         "ROI2": 2,
    ...     },
    ... )
    >>> result = map_over_labels(
    ...     segmentation,
    ...     threshold,
    ...     threshold=0.5,
    ... )
    >>> isinstance(
    ...     result,
    ...     Segmentation,
    ... )
    True
    """
    if include_background:
        labels = range(segmentation.num_labels + 1)
    else:
        labels = range(1, segmentation.num_labels + 1)

    res = [
        f(segmentation.get_label(label=label), **kwargs) for label in labels
    ]

    if return_segmentation and isinstance(res[0], sitk.Image):
        res = [sitk.Cast(r, sitk.sitkUInt8) for r in res]
        return Segmentation(
            sitk.Compose(*res),
            roi_indices=segmentation.roi_indices,
            raw_roi_names=segmentation.raw_roi_names,
        )
    return res
