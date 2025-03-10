from typing import NamedTuple  # noqa

from imgtools.modalities import Scan, Segmentation


class ImageMask(NamedTuple):
    """
    NamedTuple for storing image-mask pairs.

    Parameters
    ----------
    scan : Scan
        The scan image.
    mask : Segmentation
        The mask image.
    """

    scan: Scan
    mask: Segmentation
