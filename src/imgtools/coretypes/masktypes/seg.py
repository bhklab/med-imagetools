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

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import highdicom as hd
import numpy as np
import SimpleITK as sitk

from imgtools.coretypes import MedImage
from imgtools.coretypes.base_masks import ROIMaskMapping
from imgtools.coretypes.masktypes.roi_matching import (
    ROIMatcher,
)

# from imgtools.modalities import Scan, Segmentation
from imgtools.dicom import DicomInput, load_dicom
from imgtools.dicom.dicom_metadata import extract_metadata
from imgtools.loggers import logger

__all__ = ["SEG"]


@dataclass
class Segment:
    """
    Represents a segment in a DICOM Segmentation object.

    Parameters
    ----------
    number : int
        The segment number.
    label : str
        The label of the segment.
    description : str
        A description of the segment.
    """

    number: int
    label: str
    description: str | None = None

    def __repr__(self) -> str:
        return f"Segment(number={self.number}, label='{self.label}', description='{self.description}')"

    def __rich_repr__(self):  # noqa: ANN204
        yield "number", self.number
        yield "label", self.label
        yield "description", self.description


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

    seg_volume: hd.seg.Segmentation = field(repr=False)
    segments: dict[int, Segment] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)  # noqa

    # image: np.ndarray
    # roi_mapping: dict[str, int] = field(default_factory=dict)

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

        ds_seg = load_dicom(dicom, stop_before_pixels=False)
        seg = hd.seg.Segmentation.from_dataset(ds_seg)

        metadata = extract_metadata(ds_seg, "SEG", extra_tags=None)  # type: ignore
        segments: dict[int, Segment] = {}
        for segnum in seg.segment_numbers:
            segdesc = seg.get_segment_description(segnum)

            if segnum in segments:
                errmsg = f"Segment {segdesc.SegmentLabel} is duplicated in the DICOM-SEG file."
                raise ValueError(errmsg)
            segments[segnum] = Segment(
                number=segnum,
                label=segdesc.SegmentLabel,
                description=segdesc.get("SegmentDescription", None),
            )

        return cls(
            seg_volume=seg,
            segments=segments,
            metadata=metadata,
        )

    @property
    def labels(self) -> list[str]:
        """
        Returns a list of unique labels for the segments in the DICOM-SEG object.
        """
        return [seg.label for seg in self.segments.values()]

    @property
    def descriptions(self) -> list[str]:
        """
        Returns a list of unique descriptions for the segments in the DICOM-SEG object.
        """
        return [
            seg.description
            for seg in self.segments.values()
            if seg.description
        ]

    def extract_roi_identifiers(self) -> dict[str, int]:
        """
        Returns a mapping of ROI names to segment numbers.

        This provides a reverse mapping that can be used to match ROIs.
        For each segment, all available naming formats are included in the mapping:
        - The label (if not empty)
        - The description (if not empty)
        - "label::description" format (if both are present)

        This ensures all possible ways to reference a segment are available for matching.
        """
        names_map = {}
        for idx, seg in self.segments.items():
            # Add all available naming formats
            if seg.label:
                names_map[seg.label] = idx
            if seg.description:
                names_map[seg.description] = idx
            if seg.label and seg.description:
                names_map[f"{seg.label}::{seg.description}"] = idx
        return names_map

    @property
    def volume(self) -> hd.Volume:
        return self.seg_volume.get_volume(
            combine_segments=False, dtype=np.uint8
        )

    def get_vector_mask(
        self,
        reference_image: MedImage,
        roi_matcher: ROIMatcher,
    ) -> tuple[sitk.Image, dict[int, ROIMaskMapping]]:
        roi_identifier_mapping = self.extract_roi_identifiers()

        matched_rois: list[tuple[str, list[Segment]]] = []
        for key, matches in roi_matcher.match_rois(
            list(roi_identifier_mapping.keys())
        ):
            segs = [
                self.segments[idx]
                for idx in set(
                    roi_identifier_mapping[match] for match in matches
                )
            ]
            matched_rois.append((key, segs))

        ref_size = reference_image.size
        mask_img_size: tuple[int, int, int, int] = (
            ref_size.depth,
            ref_size.height,
            ref_size.width,
            len(matched_rois),
        )

        # this is what will be returned!
        mask_array_4d = np.zeros(
            mask_img_size,
            dtype=np.uint8,
        )

        volume = self.seg_volume.get_volume(
            combine_segments=False,
            rescale_fractional=False,
            skip_overlap_checks=False,
            segment_numbers=None,
        )

        raw_seg_mask_array = volume.array

        logger.debug(
            f"Extracting {len(matched_rois)} ROIs from DICOM-SEG file",
            mask_array_4d=mask_array_4d.shape,
            raw_seg_mask_array=volume.spatial_shape,
        )

        plane_positions = [
            p[0].ImagePositionPatient for p in volume.get_plane_positions()
        ]

        ref_indices = [
            reference_image.TransformPhysicalPointToIndex(p)
            for p in plane_positions
        ]

        # we need something to store the mapping
        # so that we can keep track of what the 3D mask matches to
        # the original roi name(s)
        mapping: dict[int, ROIMaskMapping] = {}

        for iroi, res in enumerate(matched_rois):
            segment_matches: list[Segment]
            roi_key, segment_matches = res
            assert isinstance(segment_matches, list), (
                f"Expected list of segments, got {type(segment_matches)}"
            )
            # we use the list of segments to extract the 3D array
            # from the raw_seg_mask_array
            # then for each z slice, we need to determine which index
            # in the mask mask_array_4d, which is not trivial.

            # we use the ref_indices we calculated above,
            # which should be (0,0,z) for each slice
            # and then we can use the z index to get the correct
            # slice from the raw_seg_mask_array
            for segment_of_interest in segment_matches:
                arr = raw_seg_mask_array[..., segment_of_interest.number - 1]

                # now we insert each slice into the correct index
                # in the mask_array_4d
                for (_x, _y, z), seg_slice in zip(
                    ref_indices, arr, strict=True
                ):
                    # we need to check if the z index is in bounds
                    # of the mask_array_4d
                    # mask_array_4d[:, ]
                    # mask_array_4d[ :, y, z, iroi] = seg_slice
                    if 0 <= z < mask_array_4d.shape[0]:
                        mask_array_4d[z, :, :, iroi] = np.logical_or(
                            mask_array_4d[z, :, :, iroi], seg_slice
                        )
                    else:
                        logger.warning(
                            f"Z-index {z} out of bounds for reference image shape. "
                            f"Skipping slice for ROI '{roi_key}'"
                        )
                mapping[iroi] = ROIMaskMapping(
                    roi_key=roi_key, roi_names=[*segment_matches]
                )
        mask_image = sitk.GetImageFromArray(mask_array_4d, isVector=True)
        mask_image.CopyInformation(reference_image)

        return mask_image, mapping

    def __rich_repr__(self):
        yield "segments", self.segments
        # yield "metadata", len(self.metadata)
        yield "labels", self.labels
        yield "descriptions", self.descriptions
        yield "roi_mapping", self.extract_roi_identifiers()


if __name__ == "__main__":
    from rich import print

    from imgtools.coretypes.imagetypes import Scan

    ref = Scan.from_dicom("data/NSCLC-Radiomics/LUNG1-002/CT_Series23261228")

    path = Path(
        "data/NSCLC-Radiomics/LUNG1-002/SEG_Series0515.421/00000001.dcm"
    )

    seg = SEG.from_dicom(path)
    print(seg)

    matcher = ROIMatcher(
        match_map={
            "lung": [".*lung.*"],
            "gtv": [".*gtv.*"],
            "spinalcord": [".*cord.*"],
            "esophagus": [".*esophagus.*"],
        },
        ignore_case=True,
    )

    vm, mapping = seg.get_vector_mask(ref, matcher)
