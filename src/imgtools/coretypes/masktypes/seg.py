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
from typing import TYPE_CHECKING, Any

import highdicom as hd
import numpy as np
import SimpleITK as sitk

from imgtools.coretypes.base_masks import ROIMaskMapping
from imgtools.coretypes.masktypes.roi_matching import (
    ROIMatcher,
)

# from imgtools.modalities import Scan, Segmentation
from imgtools.dicom import DicomInput, load_dicom
from imgtools.dicom.dicom_metadata import extract_metadata
from imgtools.loggers import logger

if TYPE_CHECKING:
    from imgtools.coretypes import MedImage

__all__ = ["SEG"]


@dataclass
class Segment:
    """
    Represents a segment in a DICOM Segmentation object.

    Attributes
    ----------
    number : int
        The segment number.
    label : str
        The label of the segment.
    description : str
        A description of the segment.
    data_array : np.ndarray | None
        The data array representing the segment. Defaults to None.
    """

    number: int
    label: str
    description: str | None = None
    data_array: np.ndarray | None = None

    def __repr__(self) -> str:
        return f"Segment(number={self.number}, label='{self.label}', description='{self.description}')"

    def __rich_repr__(self):  # noqa: ANN204
        yield "number", self.number
        yield "label", self.label
        yield "description", self.description
        yield (
            "data_array",
            self.data_array.shape if self.data_array is not None else None,
        )


def get_ref_indices(
    seg: hd.seg.Segmentation,
) -> np.ndarray:
    """
    Returns the reference indices for a given segmentation object.
    This function attempts to extract the reference indices from the segmentation
    object. If the segmentation is fractional, it uses the volume geometry to
    calculate the reference indices.
    If the segmentation is not fractional, it extracts the reference indices
    directly from the segmentation object.
    """
    try:
        ref_indices = np.array(
            [
                p[0].ImagePositionPatient
                for p in seg.get_volume().get_plane_positions()
            ]
        )
    except Exception as e:
        # probably fractional
        svg = seg.get_volume_geometry()

        if svg is None:
            raise ValueError(
                "Unable to get volume geometry from segmentation."
            ) from e

        ref_indices = svg.map_indices_to_reference(
            np.array([[p, 0, 0] for p in range(int(seg.NumberOfFrames))])
        )

    return ref_indices


@dataclass
class SEG:
    """Represents a DICOM Segmentation (DICOM-SEG) object."""

    raw_seg: hd.seg.Segmentation = field(repr=False)
    ref_indices: np.ndarray = field(repr=False)
    segments: dict[int, Segment] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)  # noqa

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

        ref_indices = get_ref_indices(seg)

        match hd.seg.SegmentationTypeValues(seg.SegmentationType):
            case hd.seg.SegmentationTypeValues.BINARY:
                # Binary segmentation
                for segment_number, segment in segments.items():
                    segment.data_array = (
                        seg.get_volume(
                            combine_segments=False,
                            rescale_fractional=False,
                            skip_overlap_checks=False,
                            segment_numbers=[segment_number],
                        )
                        .squeeze_channel()
                        .array
                    )

            case hd.seg.SegmentationTypeValues.FRACTIONAL:
                # should only be 1 segment
                assert len(seg.segment_numbers) == 1, (
                    f"Fractional DICOM-SEG has {len(seg.segment_numbers)} "
                    f"segments, but expected 1."
                )
                # assume that the pixel array is just for one segment
                # add to the segment
                segments[seg.segment_numbers[0]].data_array = seg.pixel_array
            case _:
                msg = f"Unsupported SegmentationType: {seg.SegmentationType}"
                raise ValueError(msg)

        # sanity check
        for segment in segments.values():
            if segment.data_array is None:
                errmsg = (
                    f"Segment {segment.number} has no data array. "
                    f"Check the DICOM-SEG file."
                )
                raise ValueError(errmsg)
            # length of ref_indices should be the same as 0th dimension of data_array
            if segment.data_array.shape[0] != len(ref_indices):
                errmsg = (
                    f"Segment {segment.number} has a data array with shape "
                    f"{segment.data_array.shape}, but expected {len(ref_indices)}."
                )
                raise ValueError(errmsg)

        return cls(
            raw_seg=seg,
            ref_indices=ref_indices,
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

        if not matched_rois:
            logger.warning(
                "No matching ROIs found. Returning empty mask.",
                roi_matcher=roi_matcher,
            )
            raise ValueError(
                "No matching ROIs found. Returning empty mask.",
            )

        ref_image_indices = [
            reference_image.TransformPhysicalPointToIndex(pos)
            for pos in self.ref_indices
        ]

        # we need something to store the mapping
        # so that we can keep track of what the 3D mask matches to
        # the original roi name(s)
        mapping: dict[int, ROIMaskMapping] = {}
        mask_images = []

        for iroi, (roi_key, segment_matches) in enumerate(matched_rois):
            mask_array_3d = np.zeros(
                (
                    reference_image.size.depth,
                    reference_image.size.height,
                    reference_image.size.width,
                ),
                dtype=np.uint8,
            )
            # we use the pre-stored data in each segment
            # then for each z slice, we need to determine which index in the output mask

            for segment_of_interest in segment_matches:
                # Use the pre-stored data_array from the segment
                arr = segment_of_interest.data_array
                if arr is None:
                    logger.warning(
                        f"Segment {segment_of_interest.number} ({segment_of_interest.label}) "
                        f"has no data array. Skipping."
                    )
                    continue

                # now we insert each slice into the correct index in the 3D mask array
                for index, seg_slice in zip(
                    ref_image_indices, arr, strict=True
                ):
                    # we need to check if the z index is in bounds of the mask_array
                    (_x, _y, z) = index
                    if 0 <= z < reference_image.size.depth:
                        mask_array_3d[z, :, :] = np.logical_or(
                            mask_array_3d[z, :, :], seg_slice
                        )
                    else:
                        logger.warning(
                            f"Z-index {z} out of bounds for reference image shape. "
                            f"Skipping slice for ROI '{roi_key}'"
                        )
                mapping[iroi] = ROIMaskMapping(
                    roi_key=roi_key,
                    roi_names=segment_matches,
                )
            mask_images.append(sitk.GetImageFromArray(mask_array_3d))

        mask_image = sitk.Compose(*mask_images)
        mask_image.CopyInformation(reference_image)

        assert mask_image.GetNumberOfComponentsPerPixel() == len(mapping)

        return mask_image, mapping

    def __rich_repr__(self):  # noqa: ANN204
        yield "segments", self.segments
        # yield "metadata", len(self.metadata)
        yield "labels", self.labels
        yield "descriptions", self.descriptions
        yield "roi_mapping", self.extract_roi_identifiers()


if __name__ == "__main__":
    from pathlib import Path

    from rich import print
    from tqdm import tqdm

    from imgtools.io.writers import ExistingFileMode, NIFTIWriter

    mask_writer = NIFTIWriter(
        root_directory=Path("temp_outputs"),
        filename_format="Case_{case_id}_{PatientID}/{Modality}_Series-{SeriesInstanceUID}/{roi_key}__[{roi_names}].nii.gz",
        existing_file_mode=ExistingFileMode.OVERWRITE,
        compression_level=5,
    )
    ref_image_writer = NIFTIWriter(
        root_directory=Path("temp_outputs"),
        filename_format="Case_{case_id}_{PatientID}/{Modality}_Series-{SeriesInstanceUID}/reference.nii.gz",
        existing_file_mode=ExistingFileMode.OVERWRITE,
        compression_level=5,
    )

    from imgtools.dicom.crawl import Crawler, CrawlerSettings
    from imgtools.dicom.interlacer import Interlacer

    directory = Path(
        "/home/gpudual/bhklab/radiomics/Projects/med-imagetools/data"
    )
    crawler = Crawler(
        CrawlerSettings(
            directory,
        )
    )
    interlacer = Interlacer(crawl_index=crawler.index)

    from imgtools.coretypes.base_masks import ROIMaskMapping, VectorMask
    from imgtools.coretypes.imagetypes import Scan

    matcher = ROIMatcher(
        match_map={
            "lung": [".*lung.*"],
            "gtv": [".*gtv.*", ".*tumor.*"],
            "Brain": [r"brain.*"],
            "spinalcord": [".*cord.*"],
            "esophagus": [".*esophagus.*"],
            "Prostate": [r"prostate.*"],
            "Femur": [r"femur.*"],
            "Bladder": [r"bladder.*"],
            "Rectum": [r"rectum.*"],
            "Heart": [r"heart.*"],
            "Liver": [r"liver.*"],
            "Kidney": [r"kidney.*"],
            "Cochlea": [r"cochlea.*"],
            "Uterus": [r"uterus.*", "ut.*"],
            "Nodules": [r".*nodule.*"],
            "lymph": [r".*lymph.*"],
            "ispy": [r".*VOLSER.*"],
            "reference": [r".*reference.*"],
        },
        ignore_case=True,
    )
    branches = [*interlacer.query("CT,SEG"), *interlacer.query("MR,SEG")]
    fails = []
    for i, (ct, *segs) in enumerate(
        tqdm(branches, desc="Processing CT and SEG files")
    ):
        ct_node = interlacer.series_nodes[ct["Series"]]
        ct_folder = directory.parent / ct_node.folder
        # seg_node = interlacer.series_nodes[segs[0]['Series']]
        scan = Scan.from_dicom(
            str(ct_folder),
            series_id=ct["Series"],
        )
        # ref_image_writer.save(
        #     scan,
        #     case_id=f"{i:>04d}",
        #     **scan.metadata,
        #     roi_key="reference",
        #     roi_names="",
        # )
        seg = None
        for seg_id in segs:
            seg_node = interlacer.series_nodes[seg_id["Series"]]
            seg_folder = directory.parent / seg_node.folder
            seg_file = list(seg_folder.glob("*.dcm"))[0]

            try:
                seg = SEG.from_dicom(
                    seg_file,
                )
                vm = VectorMask.from_seg(
                    scan,
                    seg,
                    matcher,
                )
            except Exception as e:
                logger.exception(f"{seg_file} {e} {seg}")
                fails.append((i, seg_file, e, seg))
                raise e

        #     for _index, roi_key, roi_names, mask in vm.iter_masks():
        #         mask_writer.save(
        #             mask,
        #             case_id=f"{i:>04d}",
        #             roi_key=roi_key,
        #             roi_names="|".join(roi_names),
        #             **mask.metadata,
        #         )
        #         break
        #     break
        # break
