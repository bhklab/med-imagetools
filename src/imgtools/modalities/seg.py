from __future__ import annotations
from dataclasses import dataclass, field
import re
from collections import defaultdict

import SimpleITK as sitk
import highdicom as hd
import numpy as np

from imgtools.loggers import logger
from imgtools.modalities.segmentation import Segmentation

__all__ = ["SEG"]

@dataclass
class SEG(sitk.Image):
    """
    A class for representing a DICOM-SEG.
    """

    image: sitk.Image
    metadata: dict[str, str] = field(default_factory=dict)
    roi_mapping: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        super().__init__(self.image)
    
    @classmethod
    def from_dicom(cls, path: str, metadata: object) -> SEG:
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

            image = sitk.Compose([sitk.GetImageFromArray(mask) for mask in combined_masks])

        else:
            image_array = sitk.GetArrayFromImage(sitk.ReadImage(path))
            image_array[image_array > 1] = 1
            image = sitk.Compose([sitk.GetImageFromArray(image_array)])
            roi_mapping = {metadata.SegmentSequence[0].SegmentLabel: 1}

        logger.info(
            "Read DICOM-SEG",
            path=path,
            roi_mapping=roi_mapping,
        )

        return cls(image, metadata=dict(metadata), roi_mapping=roi_mapping)

    def __getitem__(self, idx) -> sitk.Image:
        return sitk.VectorIndexSelectionCast(self, idx-1)
    
    def to_segmentation(
        self,
        reference_image: sitk.Image,
        roi_names: dict[str, str] | None = None,
        roi_select_first: bool = False,
        roi_separate: bool = False,
        ignore_missing_regex: bool = False,
        **kwargs
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

        # If no filtering needed, return as-is
        if roi_names is None:
            if self.GetSize() == reference_image.GetSize():
                self.CopyInformation(reference_image)
            else:
                logger.warning(
                    "Reference image and segmentation have different sizes. "
                    "Skipping spatial information copy."
                )
            return Segmentation(
                segmentation=self, 
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
                            (label_name, sitk.GetArrayFromImage(self[idx])))
                else:
                    mask = [sitk.GetArrayFromImage(self[idx]) for idx in indices]
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

    ref = read_dicom_auto('data/NSCLC-Radiomics/LUNG1-002/CT_Series-61228')

    res = seg.to_segmentation(ref, roi_names={"lung": "lung"})
