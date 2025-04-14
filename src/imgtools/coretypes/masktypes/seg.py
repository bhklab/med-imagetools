"""
SEG Module

This module defines the `SEG` class, which represents a DICOM-SEG (Segmentation) object.
It provides functionalities for loading segmentation data from DICOM files, extracting
region-of-interest (ROI) masks, and aligning segmentation masks with reference images.

Key Functionalities
-------------------
1. **Loading DICOM-SEG Data**
   - Reads segmentation masks from DICOM-SEG files.
   - Supports multi-segment DICOM-SEG files and fractional segmentation masks..

2. **Aligning Segmentation to Reference Scans**
   - Maps segmentation frames to reference images using SOPInstanceUID.
   - Ensures spatial alignment for accurate analysis.

3. **Converting SEG to Usable Mask Formats**
   - Transforms segmentation masks into structured mask representations.
   - Allows filtering and renaming of ROIs using regex-based matching.

Examples
--------
>>> from pydicom import dcmread
>>> from pathlib import Path
>>> from imgtools.io.loaders.utils import (
...     read_dicom_auto,
... )
>>> from imgtools.modalities import SEG
>>> path = "data/NSCLC-Radiomics/LUNG1-002/SEG_Series-5.421/00000001.dcm"
>>> meta = dcmread(path, stop_before_pixels=True)
>>> seg = SEG.from_dicom(path, meta)
>>> ref = read_dicom_auto(
...     "data/NSCLC-Radiomics/LUNG1-002/CT_Series-61228"
... )
>>> res = seg.to_segmentation(
...     ref, roi_names={"lung": "lung"}
... )
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import highdicom as hd
import numpy as np
import SimpleITK as sitk

# from imgtools.modalities import Scan, Segmentation
from imgtools.dicom import DicomInput, load_dicom
from imgtools.dicom.dicom_metadata import extract_metadata
from imgtools.loggers import logger

__all__ = ["SEG"]


@dataclass
class SEG:
    """
    Represents a DICOM Segmentation (DICOM-SEG) object.

    This class provides functionalities to load, store, and manipulate DICOM-SEG
    data, including extracting region-of-interest (ROI) masks, aligning segmentations
    with reference images, and converting segmentation masks into structured formats.

    Parameters
    ----------
    image : np.ndarray
        A 4D array representing the segmentation mask(s).
        (depth, height, width, num_segments)
    metadata : dict[str, str], optional
        Metadata associated with the segmentation, stored as a dictionary.
        Defaults to an empty dictionary.
    roi_mapping : dict[str, int], optional
        A mapping of ROI labels to their corresponding segmentation indices.
        Defaults to an empty dictionary.
    raw_dicom_meta : DicomInput, optional
        The raw DICOM metadata from which the segmentation was extracted.
        Defaults to None.
    """

    image: np.ndarray
    metadata: dict[str, str] = field(default_factory=dict)
    roi_mapping: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dicom(cls, dicom: DicomInput) -> SEG:
        """
        Loads a DICOM-SEG object from a DICOM file.
        """
        if isinstance(dicom, (str, Path)):
            dicom = Path(dicom)
            if dicom.is_dir():
                if len(list(dicom.glob("*.dcm"))) == 1:
                    dicom = list(dicom.glob("*.dcm"))[0]
                else:
                    errmsg = (
                        f"Directory `{dicom}` contains multiple DICOM files. "
                        f"Cannot determine which one to load."
                    )
                    raise ValueError(errmsg)

        dicom_seg = load_dicom(dicom)
        metadata = extract_metadata(dicom_seg, "SEG", extra_tags=None)

        seg = hd.seg.Segmentation.from_dataset(dicom_seg)
        array = seg.get_volume(combine_segments=False, dtype=np.uint8).array

        logger.debug('loaded DICOM-SEG', path=dicom, array=array.shape)

        


        raise NotImplementedError()
        # segment_sequence = metadata.SegmentSequence
        # if len(segment_sequence) > 1:
        #     seg = hd.seg.segread(path)
        #     array = seg.get_volume(
        #         combine_segments=False, dtype=np.uint8
        #     ).array
        #     array[array > 1] = 1
        #     mask_groups = defaultdict(
        #         list
        #     )  # Consolidate masks with the same name

        #     for i, segment in enumerate(segment_sequence):
        #         label = segment.SegmentLabel
        #         mask_groups[label].append(
        #             array[..., i]
        #         )  # Store masks for this label

        #     # Combine masks with the same label
        #     combined_masks = []
        #     roi_mapping = {}
        #     for idx, (label, masks) in enumerate(mask_groups.items()):
        #         combined_masks.append(
        #             np.logical_or.reduce(masks).astype(np.uint8)
        #         )
        #         roi_mapping[label] = idx + 1

        #     image = np.stack(combined_masks, axis=-1)

        # else:
        #     image_array = sitk.GetArrayFromImage(sitk.ReadImage(path))
        #     if getattr(metadata, "SegmentationType", None) == "FRACTIONAL":
        #         maximum_fractional_value = metadata.MaximumFractionalValue
        #         image_array = (
        #             image_array.astype(np.float32) / maximum_fractional_value
        #         )
        #     else:
        #         image_array[image_array > 1] = 1
        #         image_array = image_array.astype(np.uint8)

        #     roi_mapping = {segment_sequence[0].SegmentLabel: 1}
        #     image = np.stack([image_array], axis=-1)

        # logger.info(
        #     "Read DICOM-SEG",
        #     path=path,
        #     roi_mapping=roi_mapping,
        # )

        # return cls(
        #     image,
        #     metadata=dict(metadata),
        #     roi_mapping=roi_mapping,
        #     raw_dicom_meta=metadata,
        # )  # type: ignore


if __name__ == "__main__":
    from pydicom import dcmread

    from imgtools.io.loaders.utils import read_dicom_auto

    path = "data/NSCLC-Radiomics/LUNG1-002/SEG_Series-5.421/00000001.dcm"
    meta = dcmread(path, stop_before_pixels=True)

    seg = SEG.from_dicom(path, meta)

    ref = read_dicom_auto("data/NSCLC-Radiomics/LUNG1-002/CT_Series-61228")

    res = seg.to_segmentation(ref, roi_names={"lung": "lung"})  # type: ignore
