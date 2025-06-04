from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import highdicom as hd
import numpy as np
import SimpleITK as sitk

from imgtools.coretypes.base_masks import ROIMaskMapping, VectorMask
from imgtools.coretypes.masktypes.roi_matching import (
    ROIMatchFailurePolicy,
    ROIMatchingError,
)

# from imgtools.modalities import Scan, Segmentation
from imgtools.dicom import DicomInput, load_dicom
from imgtools.dicom.dicom_metadata import extract_metadata
from imgtools.loggers import logger

if TYPE_CHECKING:
    import rich.repr

    from imgtools.coretypes import MedImage
    from imgtools.coretypes.masktypes.roi_matching import (
        ROIMatcher,
    )

__all__ = [
    "SEG",
    "SegmentationTypeUnsupportedError",
    "SegmentDuplicateError",
    "SegmentDataMissingError",
    "SegmentReferenceIndicesError",
    "SegmentationValidationError",
]


class SegmentationError(Exception):
    """Base exception for DICOM SEG errors."""

    pass


class SegmentationTypeUnsupportedError(SegmentationError):
    """Raised when the segmentation type is unsupported."""

    def __init__(self, seg_type: str) -> None:
        self.seg_type = seg_type
        message = f"Unsupported SegmentationType: {seg_type}"
        super().__init__(message)


class SegmentDuplicateError(SegmentationError):
    """Raised when a segment is duplicated in the DICOM-SEG file."""

    def __init__(self, segment_label: str, segment_number: int) -> None:
        self.segment_label = segment_label
        self.segment_number = segment_number
        message = f"Segment {segment_label} (number: {segment_number}) is duplicated in the DICOM-SEG file."
        super().__init__(message)


class SegmentDataMissingError(SegmentationError):
    """Raised when a segment has no data array."""

    def __init__(self, segment_number: int, segment_label: str) -> None:
        self.segment_number = segment_number
        self.segment_label = segment_label
        message = f"Segment {segment_number} ({segment_label}) has no data array. Check the DICOM-SEG file."
        super().__init__(message)


class SegmentReferenceIndicesError(SegmentationError):
    """Raised when there's an error with reference indices in the segmentation."""

    def __init__(self, error_message: str) -> None:
        message = f"Unable to get reference indices from segmentation: {error_message}"
        super().__init__(message)


class SegmentationValidationError(SegmentationError):
    """Raised when a segmentation validation check fails."""

    def __init__(
        self,
        segment_number: int,
        segment_label: str,
        data_array_shape: tuple,
        ref_indices_length: int,
    ) -> None:
        self.segment_number = segment_number
        self.segment_label = segment_label
        self.data_array_shape = data_array_shape
        self.ref_indices_length = ref_indices_length
        message = (
            f"Segment {segment_number} ({segment_label}) has a data array with shape "
            f"{data_array_shape}, but expected first dimension to be {ref_indices_length}."
        )
        super().__init__(message)


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

    def __rich_repr__(self) -> rich.repr.Result:
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
            raise SegmentReferenceIndicesError(
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
    def from_dicom(  # noqa: PLR0912
        cls,
        dicom: DicomInput,
        metadata: dict[str, Any] | None = None,
    ) -> SEG:
        """
        Loads a DICOM-SEG object from a DICOM file.
        """
        if isinstance(dicom, (str, Path)):
            dicom = Path(dicom)
            if dicom.is_dir():
                if len(list(dicom.glob("*.dcm"))) == 1:
                    dicom = list(dicom.glob("*.dcm"))[0]
                else:
                    msg = (
                        f"Directory `{dicom}` contains multiple DICOM files. "
                        f"Cannot determine which one to load."
                    )
                    raise SegmentationError(msg)
        ds_seg = load_dicom(dicom, stop_before_pixels=False)
        try:
            seg = hd.seg.Segmentation.from_dataset(ds_seg)
        except KeyError as e:
            #  check if KeyError: (0062,000A)
            msg = (
                f"Segmentation object {dicom!r} does not contain "
                f"SegmentationType. Skipping."
            )
            raise SegmentationError(msg) from e

        metadata = metadata or extract_metadata(ds_seg, "SEG", extra_tags=None)  # type: ignore
        segments: dict[int, Segment] = {}
        for segnum in seg.segment_numbers:
            segdesc = seg.get_segment_description(segnum)

            if segnum in segments:
                raise SegmentDuplicateError(segdesc.SegmentLabel, segnum)
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
                raise SegmentationTypeUnsupportedError(seg.SegmentationType)

        # sanity check
        for segment in segments.values():
            if segment.data_array is None:
                raise SegmentDataMissingError(segment.number, segment.label)
            # length of ref_indices should be the same as 0th dimension of data_array
            if segment.data_array.shape[0] != len(ref_indices):
                raise SegmentationValidationError(
                    segment.number,
                    segment.label,
                    segment.data_array.shape,
                    len(ref_indices),
                )

        return cls(
            raw_seg=seg,
            ref_indices=ref_indices,
            segments=segments,
            metadata={k: v for k, v in metadata.items() if v},
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
    ) -> VectorMask | None:
        """
        Convert the SEG segments to a VectorMask using ROI matching.

        Parameters
        ----------
        reference_image : MedImage
            The reference image to align the mask with.
        roi_matcher : ROIMatcher
            The matcher used to match segment identifiers to ROI keys.

        Returns
        -------
        VectorMask | None
            A VectorMask representation of the matched segments, or None if
            no matches were found and the ROIMatchFailurePolicy is not ERROR.

        Raises
        ------
        SegmentationError
            If no segments matched the specified patterns and the ROIMatchFailurePolicy is ERROR.
        """
        roi_identifier_mapping = self.extract_roi_identifiers()
        roi_names = self.labels

        matched_results = roi_matcher.match_rois(
            list(roi_identifier_mapping.keys())
        )

        # Handle the case where no matches were found, according to the policy
        if not matched_results:
            message = "No ROIs matched any patterns in the match_map."
            match roi_matcher.on_missing_regex:
                case ROIMatchFailurePolicy.IGNORE:
                    # Silently return None
                    pass
                case ROIMatchFailurePolicy.WARN:
                    logger.warning(
                        message,
                        roi_names=list(roi_identifier_mapping.keys()),
                        roi_matching=roi_matcher.match_map,
                    )
                case ROIMatchFailurePolicy.ERROR:
                    # Raise an error
                    errmsg = f"{message} Available ROIs: {list(roi_identifier_mapping.keys())}, "
                    raise ROIMatchingError(
                        errmsg,
                        roi_names=roi_names,
                        match_patterns=roi_matcher.match_map,
                    )
            return None

        # Process the matches and build the segments
        matched_rois: list[tuple[str, list[Segment]]] = []
        for key, matches in matched_results:
            segs = [
                self.segments[idx]
                for idx in set(
                    roi_identifier_mapping[match] for match in matches
                )
            ]
            matched_rois.append((key, segs))

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
                    image_id=roi_key
                    if roi_matcher.handling_strategy.value == "merge"
                    else f"{roi_key}__[{segment_matches[0].label}::{segment_matches[0].description}]",
                )
            mask_images.append(sitk.GetImageFromArray(mask_array_3d))

        mask_image = sitk.Compose(*mask_images)
        mask_image.CopyInformation(reference_image)

        assert mask_image.GetNumberOfComponentsPerPixel() == len(mapping)

        # Update the map to be to strings, not segments
        for idx, m in mapping.items():
            mapping[idx] = ROIMaskMapping(
                roi_key=m.roi_key,
                roi_names=[
                    f"{segment.label}::{segment.description}"
                    for segment in m.roi_names
                ],
                image_id=m.image_id,
            )

        return VectorMask(
            image=mask_image,
            roi_mapping=mapping,
            metadata=self.metadata,
            errors=None,
        )

    def __rich_repr__(self) -> rich.repr.Result:
        yield "segments", self.segments
        # yield "metadata", len(self.metadata)
        yield "labels", self.labels
        yield "descriptions", self.descriptions
        yield "roi_mapping", self.extract_roi_identifiers()
