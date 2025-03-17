from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import highdicom as hd
import numpy as np
import SimpleITK as sitk

from imgtools.loggers import logger
from imgtools.modalities import Scan, Segmentation

if TYPE_CHECKING:
    from imgtools.dicom.input.dicom_reader import DicomInput

__all__ = ["SEG"]


@dataclass
class SEG:
    """
    A class for representing a DICOM-SEG.
    """

    image: np.ndarray
    metadata: dict[str, str] = field(default_factory=dict)
    roi_mapping: dict[str, int] = field(default_factory=dict)
    raw_dicom_meta: DicomInput | None = field(default=None)
    
    @classmethod
    def from_dicom(cls, path: str, metadata: DicomInput) -> SEG:
        if len(metadata.SegmentSequence) > 1:
            seg = hd.seg.segread(path)
            array = seg.get_volume(combine_segments=False, dtype=int).array
            array[array > 1] = 1
            mask_groups = defaultdict(list)  # Consolidate masks with the same name

            for i, segment in enumerate(metadata.SegmentSequence):
                label = segment.SegmentLabel
                mask_groups[label].append(array[..., i])  # Store masks for this label

            # Combine masks with the same label
            combined_masks = []
            roi_mapping = {}
            for idx, (label, masks) in enumerate(mask_groups.items()):
                combined_masks.append(np.logical_or.reduce(masks).astype(np.uint8))
                roi_mapping[label] = idx + 1

            image = np.stack(combined_masks, axis=-1)

        else:
            image_array = sitk.GetArrayFromImage(sitk.ReadImage(path))
            image_array[image_array > 1] = 1
            image = np.stack([image_array], axis=-1)
            roi_mapping = {metadata.SegmentSequence[0].SegmentLabel: 1}

        logger.info(
            "Read DICOM-SEG",
            path=path,
            roi_mapping=roi_mapping,
        )

        return cls(image, metadata=dict(metadata), roi_mapping=roi_mapping, raw_dicom_meta=metadata)

    def __getitem__(self, idx: int | str) -> np.ndarray:
        """Get the binary mask for a given ROI index or label.

        Parameters
        ----------
        idx : int | str
            The ROI index (1-indexed) or label.

        Returns
        -------
        np.ndarray
            The binary mask for the given ROI index or label.
        """
        if isinstance(idx, str):
            roi_idx = self.roi_mapping.get(idx)
            if roi_idx is None:
                msg = f"Unknown ROI label: {idx}"
                raise ValueError(msg)
            mask = self.image[..., roi_idx - 1]
        else:
            mask = self.image[..., idx - 1]
        return mask
    
    def _get_sop_uid(self, idx: int) -> str:
        """
        Gets the SOPInstanceUID from the raw DICOM metadata for a given frame index.

        Parameters
        ----------
        idx : int
            The frame index.

        Returns
        -------
        str
            The SOPInstanceUID for the given frame index.
        """
        per_frame_seq = getattr(self.raw_dicom_meta, "PerFrameFunctionalGroupsSequence", None)
        ref_series_seq = getattr(self.raw_dicom_meta, "ReferencedSeriesSequence", None)
        src_img_seq = getattr(self.raw_dicom_meta, "SourceImageSequence", None)

        # Case 1: Check if DerivationImageSequence exists in the per-frame sequence
        if per_frame_seq and idx:
            derivation_seq = getattr(per_frame_seq[idx], "DerivationImageSequence", None)
            if derivation_seq:
                return str(derivation_seq[0].SourceImageSequence[0].ReferencedSOPInstanceUID)

        # Case 2: Check ReferencedSeriesSequence
        if ref_series_seq:
            ref_instance_seq = getattr(ref_series_seq[0], "ReferencedInstanceSequence", None)
            if ref_instance_seq:
                return str(ref_instance_seq[idx].ReferencedSOPInstanceUID)

        # Case 3: Default to SourceImageSequence
        if src_img_seq:
            return str(src_img_seq[idx].ReferencedSOPInstanceUID)
    
        raise KeyError(f"Couldn't find Referenced SOPInstanceUID in metadata for index {idx}.")
    
    def _align_to_reference(self, reference_image: Scan) -> None:
        """
        Aligns the segmentation mask to the provided reference image by mapping the SOPInstanceUIDs.

        The method iterates over the segmentation mask frames and assigns each frame to the corresponding
        frame in the reference image, based on the mapping provided in the reference image's metadata.
        The mapping is expected to be stored in the "SOPInstanceUIDMapping" key.

        Parameters
        ----------
        reference_image : Scan
            The reference image to which the segmentation mask is aligned.

        """
        reference_array = sitk.GetArrayFromImage(reference_image)

        new_image = np.zeros((reference_array.shape[0],) + self.image.shape[1:])

        sop_uid_mapping = eval(reference_image.GetMetaData("SOPInstanceUIDMapping"))

        for idx in range(self.image.shape[0]):
            sop_uid = self._get_sop_uid(idx)
            if sop_uid in sop_uid_mapping:
                new_image[int(sop_uid_mapping[sop_uid])] = self.image[idx]

        self.image = new_image  
            
    def to_segmentation(
        self,
        reference_image: Scan,
        roi_names: dict[str, str] | None = None,
        roi_select_first: bool = False,
        roi_separate: bool = False,
        ignore_missing_regex: bool = False,
    ) -> Segmentation:
        """
        Converts the segmentation into a mask based on ROI names.

        Parameters
        ----------
        reference_image : sitk.Image
            The reference image to copy spatial information from.
        roi_names : dict[str, str], optional
            A dictionary where keys are label names, and values are regex patterns to match in self.roi_mapping.
            If None, all ROIs will be included.
        roi_select_first : bool, default=False
            If True, selects only the first matching ROI for each regex pattern.
        roi_separate : bool, default=False
            If True, assigns separate labels for each match by appending a numerical suffix.
        ignore_missing_regex : bool, default=False
            If True, returns None if no ROIs match the regex patterns.
        
        Returns
        -------
        Segmentation
            A new segmentation object containing the filtered mask.
        """

        self._align_to_reference(reference_image)

        # If no filtering needed, return as-is
        if roi_names is None:
            combined_image = sitk.Compose([
                sitk.GetImageFromArray(self[idx]) for idx in range(len(self.roi_mapping))
            ])
            combined_image.CopyInformation(reference_image)
            return Segmentation(
                segmentation=combined_image, 
                metadata=self.metadata, 
                roi_indices=self.roi_mapping
            )

        # Step 1: Find matching ROI indices
        matched_segments = defaultdict(list)
        for label, regex in roi_names.items():
            pattern = re.compile(regex, re.IGNORECASE)
            for seg_label, seg_num in self.roi_mapping.items():
                if pattern.match(seg_label):
                    matched_segments[label].append(seg_num)

        if not matched_segments:
            if not ignore_missing_regex:
                    msg = (
                        f"No ROIs matching {roi_names} found in {self.roi_mapping.keys()}."
                    )
                    raise ValueError(msg)
            else:
                return None
        
        logger.info(
            "Matching ROIs",
            matched_segments=matched_segments,
        )
        
        # Step 2: Select first match if required
        if roi_select_first:
            matched_segments = {k: [v[0]] for k, v in matched_segments.items() if v}

        # Step 3: Extract and combine masks
        extracted_masks = []
        for label, indices in matched_segments.items():
                if roi_separate:
                    for idx in indices:
                        label_name = f"{label}_{idx}" if idx > 0 else label
                        extracted_masks.append(
                            (label_name, self[idx]))
                else:
                    mask = [self[idx] for idx in indices]
                    mask = np.logical_or.reduce(mask).astype(np.uint8)
                    extracted_masks.append((label, mask))

        # Step 4: Convert masks to sitk.Images
        sitk_images = [sitk.GetImageFromArray(mask) for _, mask in extracted_masks]
        combined_image = sitk.Compose(sitk_images)
        combined_image.CopyInformation(reference_image)

        # Step 5: Create new roi_mapping
        new_roi_mapping = {name: i for i, (name, _) in enumerate(extracted_masks)}

        return Segmentation(
            segmentation=combined_image, 
            metadata=self.metadata, 
            roi_indices=new_roi_mapping
        )
        
if __name__ == "__main__":
    from pydicom import dcmread

    from imgtools.io.loaders.utils import read_dicom_auto

    path = "data/NSCLC-Radiomics/LUNG1-002/SEG_Series-5.421/00000001.dcm"
    meta = dcmread(path, stop_before_pixels=True)

    seg = SEG.from_dicom(path, meta)

    ref = read_dicom_auto("data/NSCLC-Radiomics/LUNG1-002/CT_Series-61228")

    res = seg.to_segmentation(ref, roi_names={"lung": "lung"})
