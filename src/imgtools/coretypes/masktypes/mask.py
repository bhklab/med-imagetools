from __future__ import annotations

from collections.abc import Mapping
from typing import Iterator

import numpy as np
import SimpleITK as sitk

from imgtools.coretypes.imagetypes.med_image import MedImage
from imgtools.coretypes.masktypes.roi_matching import ROIMaskMapping


class Mask(MedImage):
    """A label mask where each voxel holds a single segmentation label."""

    @property
    def unique_labels(self) -> np.ndarray:
        """Return all unique labels present in the mask."""
        arr, _ = self.to_numpy()
        return np.unique(arr)

    def to_vector_mask(self) -> VectorMask:
        """Convert a label image to a vector mask (one-hot per label)."""
        # TODO:: I dont think this always works...
        arr, _ = self.to_numpy()
        n_labels = int(np.max(arr)) + 1
        one_hot = np.zeros((*arr.shape, n_labels), dtype=np.uint8)
        for i in range(1, n_labels):  # skip background 0
            one_hot[..., i][arr == i] = 1
        vec_img = sitk.GetImageFromArray(one_hot)
        vec_img.CopyInformation(self)
        return VectorMask(vec_img)


class VectorMask(MedImage):
    """A multi-label segmentation image with vector-valued binary mask pixels."""

    roi_mapping: Mapping[int, ROIMaskMapping]

    def __init__(
        self,
        image: sitk.Image,
        roi_mapping: Mapping[int, ROIMaskMapping] | None = None,
    ) -> None:
        super().__init__(image)
        self.roi_mapping = roi_mapping or {}

    @property
    def n_masks(self) -> int:
        """Number of binary mask channels (components per voxel)."""
        return self.GetNumberOfComponentsPerPixel()

    @property
    def roi_keys(self) -> list[str]:
        """List of all available ROI keys."""
        return [v.roi_key for v in self.roi_mapping.values()]

    def extract_mask(self, key_or_index: str | int) -> Mask:
        """Extract a single binary mask as a `Mask`, via index or ROI key."""
        if isinstance(key_or_index, int):
            if not (0 <= key_or_index < self.n_masks):
                msg = f"Invalid mask index {key_or_index}"
                raise IndexError(msg)
            return self._extract_mask_by_index(key_or_index)

        if isinstance(key_or_index, str):
            # find index corresponding to ROI key
            for i, mapping in self.roi_mapping.items():
                if mapping.roi_key == key_or_index:
                    return self._extract_mask_by_index(i)
            msg = f"ROI key '{key_or_index}' not found in mapping."
            raise KeyError(msg)

        raise TypeError("Key must be an int index or str ROI key.")

    def _extract_mask_by_index(self, index: int) -> Mask:
        """Low-level helper to extract mask by index."""
        slice_img = sitk.VectorIndexSelectionCast(self, index)
        return Mask(slice_img)

    def iter_masks(self) -> Iterator[tuple[int, str, Mask]]:
        """Yield (index, roi_key, mask) for each mask component."""
        for i in range(self.n_masks):
            key = self.roi_mapping.get(i, ROIMaskMapping(str(i), []))
            yield i, key.roi_key, self._extract_mask_by_index(i)
