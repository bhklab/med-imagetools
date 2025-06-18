from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterator, Mapping

import numpy as np
import SimpleITK as sitk

from imgtools.coretypes import MedImage
from imgtools.coretypes.box import RegionBox
from imgtools.loggers import logger

if TYPE_CHECKING:
    from imgtools.coretypes.masktypes.seg import SEG
    from imgtools.coretypes.masktypes.structureset import (
        ROIMatcher,
        RTStructureSet,
    )

# we dont have to use a named tuple here, but its simple and easy to read
ROIMaskMapping = namedtuple(
    "ROIMaskMapping", ["roi_key", "roi_names", "image_id"]
)


class TooManyComponentsError(ValueError):
    """Raised when attempting to encode a mask with more components than supported by the available integer types."""

    def __init__(self, n_components: int, max_supported: int = 32) -> None:
        msg = (
            f"Cannot encode masks with {n_components} components: "
            f"maximum supported is {max_supported} due to bitmask size limits."
        )
        super().__init__(msg)
        self.n_components = n_components
        self.max_supported = max_supported


class VectorMask(MedImage):
    """A multi-label binary mask image with vector pixels (sitkVectorUInt8).

    This class represents 3D multi-label mask images stored as SimpleITK vector images.
    Each voxel in the image contains a vector of values, where each component in the
    vector represents a binary indicator (0 or 1) for a specific label/ROI.

    The VectorMask design supports non-overlapping and overlapping segmentations,
    preserving metadata from the RTSTRUCT/SEG DICOM file.
    The dimensionality (3D) is inherited from the reference image which the
    RTSTR/SEG was constructed from.

    Background is handled automatically:
    - Index 0 is always reserved for the background, calculated as the
        absence of any ROI across all components of the vectors.
    - When extracting an ROI from the mask, the background is handled implicitly

    Properties
    ----------
    n_masks : int
        Number of binary mask channels (components per voxel)
        Does *not* include the background channel
    roi_keys : list[str]
        List of ROI keys from mapping, excluding the background

    Attributes
    ----------
    roi_mapping : dict[int, ROIMaskMapping]
        Mapping from integer indices to ROIMaskMapping objects
    metadata : dict[str, str]
        Dictionary containing metadata about the mask
    errors : dict[str, Exception] | None
        Dictionary with error messages from ROI extraction, if any

    Methods
    -------
    iter_masks(include_background: bool = False) -> Iterator[tuple[int, str, list[str], Mask]]
        Yield (index, roi_key, roi_names, Mask) for each mask channel
    has_overlap() -> bool
        Return True if any voxel has >1 mask. Determined by summing
        each voxel's vector components and checking if >1
    extract_mask(key: str | int) -> Mask
        Extract a single binary mask by index or ROI key
        Output will have a single label == 1, output type is `sitk.sitkUInt8`
    __getitem__(key)
        Allow accessing masks via indexing
        First tries to `extract_mask(key)` using the given key
        If that fails, falls back to the standard sitk.Image behavior
    """

    __match_args__ = ("roi_mapping", "metadata")

    roi_mapping: dict[int, ROIMaskMapping]
    metadata: dict[str, str]
    errors: Mapping[str, Exception] | None

    _mask_cache: dict[str | int, Mask]

    def __init__(
        self,
        image: sitk.Image,
        roi_mapping: dict[int, ROIMaskMapping],
        metadata: dict[str, str],
        errors: Mapping[str, Exception] | None = None,
    ) -> None:
        """
        Parameters
        ----------
        image : sitk.Image
            A SimpleITK image with pixel type sitk.sitkVectorUInt8
        roi_mapping : dict[int, ROIMaskMapping]
            Mapping from integer indices to ROIMaskMapping objects
            containing roi_key and roi_names
        metadata : dict[str, str]
            Dictionary containing metadata about the mask
        errors : dict[str, Exception] | None, optional
            Optional dictionary with error messages from ROI extraction, by default None
        """
        super().__init__(image)
        # Shift index to start from 1 for user-facing keys
        self.roi_mapping = {}

        if 0 in roi_mapping and roi_mapping[0].roi_key == "Background":
            # Background is already set to 0, no need to change
            self.roi_mapping = roi_mapping
        elif 0 in roi_mapping:
            # Background is not set to 0, so we need to adjust the mapping
            self.roi_mapping[0] = ROIMaskMapping(
                "Background", ["Background"], "Background"
            )
            for old_idx, roi_mask_mapping in roi_mapping.items():
                self.roi_mapping[old_idx + 1] = roi_mask_mapping
        else:
            # no background, so just set 0 and keep the rest
            self.roi_mapping[0] = ROIMaskMapping(
                "Background", ["Background"], "Background"
            )
            for old_idx, roi_mask_mapping in roi_mapping.items():
                self.roi_mapping[old_idx] = roi_mask_mapping

        self.metadata = metadata
        self.errors = errors
        self._mask_cache = {}

    def __post_init__(self) -> None:
        if self.dtype != sitk.sitkVectorUInt8:
            msg = f"Expected sitkVectorUInt8, got {self.dtype=} instead."
            msg += f" {self.dtype_str=}"
            raise TypeError(msg)

    @property
    def n_masks(self) -> int:
        """Number of binary mask channels (components per voxel).
        Notes
        -----
        This does *not* include the background channel.
        The background channel is always the first channel (index 0).
        """
        return self.GetNumberOfComponentsPerPixel()

    @property
    def roi_keys(self) -> list[str]:
        """List of ROI keys from mapping"""
        return [mapping.roi_key for mapping in self.roi_mapping.values()]

    def __getitem__(self, key):  # type: ignore # noqa
        """Allow accessing masks via indexing.

        This method first tries to extract a mask using the given key.
        If that fails, it falls back to the standard sitk.Image behavior.

        Parameters
        ----------
        key : str or int
            Either an ROI key (string) or an index (integer)

        Returns
        -------
        Mask or whatever sitk.Image.__getitem__ returns
            If the key corresponds to a mask, returns the extracted Mask.
            Otherwise, returns the result of the parent class's __getitem__.
        """
        try:
            return self.extract_mask(key)
        except (IndexError, KeyError, TypeError):
            # If extract_mask fails, fall back to standard behavior
            return super().__getitem__(key)

    def iter_masks(
        self, include_background: bool = False
    ) -> Iterator[tuple[int, str, list[str], str, Mask]]:
        """Yield (index, roi_key, roi_names, image_id, Mask) for each mask channel."""
        for i, mapping in self.roi_mapping.items():
            if i == 0 and not include_background:
                continue
            yield (
                i,
                mapping.roi_key,
                mapping.roi_names,
                mapping.image_id,
                self.extract_mask(i),
            )

    def has_overlap(self) -> bool:
        """Return True if any voxel has >1 mask"""
        arr = sitk.GetArrayFromImage(self)
        return self.n_masks > 1 and bool(np.any(np.sum(arr, axis=-1) > 1))

    def _to_label_array(self, allow_overlap: bool) -> Mask:
        """
        Convert vector mask to 3D label array with unique label per mask.

        Parameters
        ----------
        allow_overlap : bool
            If True, overlapping voxels are allowed and resolved by assigning the label of the highest-index region.
            If False, a ValueError is raised if overlaps are found.

        Returns
        -------
        Mask
            A single-channel binary mask where each voxel belongs to at most one class.
            The output is a standard Mask with pixel type sitk.sitkUInt8 or sitk.sitkLabelUInt8.
        """

        if self.n_masks == 1:  # Already a label image
            return Mask(
                sitk.Cast(self[1], sitk.sitkUInt8),
                metadata=self.metadata.copy(),
            )

        if self.has_overlap():
            if allow_overlap:
                logger.warning(
                    "Vector mask has overlaps. "
                    "Converting to sparse mask will result in a lossy conversion."
                )
            else:
                raise ValueError(
                    "Cannot convert to label image: overlap detected. "
                    "Use `to_sparse_mask()` for lossy conversion that resolves overlaps by label order."
                    "Or use `to_region_mask()` for lossless conversion that creates a new region per overlap."
                )

        arr = sitk.GetArrayFromImage(self)

        # Assign label index (1-based, since 0 = background)
        label_arr = np.zeros(arr.shape[:3], dtype=np.uint8)

        for i in range(arr.shape[-1]):
            label_arr[arr[..., i] == 1] = i + 1

        label_img = sitk.GetImageFromArray(label_arr)
        label_img.CopyInformation(self)

        # Attach merged metadata
        return Mask(
            sitk.Cast(label_img, sitk.sitkUInt8),
            metadata=self.metadata.copy(),
        )

    def to_sparse_mask(self) -> Mask:
        """Convert the vector mask to a single-channel binary mass.

        Creates a sparse representation where each voxel is assigned to exactly one class,
        even if there are overlaps in the original vector mask. In case of overlaps,
        the mask with the highest index is chosen.

        Returns
        -------
        Mask
            A single-channel binary mask where each voxel belongs to at most one class.
            The output is a standard Mask with pixel type sitk.sitkUInt8 or sitk.sitkLabelUInt8.

        Notes
        -----
        This is a lossy conversion when overlaps exist, as only one label can be
        preserved per voxel. If preserving all overlapping labels is important,
        keep working with the original VectorMask.
        """

        return self._to_label_array(allow_overlap=True)

    def to_label_image(self) -> Mask:
        """Convert the vector mask to a scalar label image with unique labels for each ROI.

        Generates a single multi-label mask where each voxel contains one integer value
        representing its class. This conversion only works if there are no overlapping
        ROIs in the vector mask.

        Returns
        -------
        Mask
            A multi-label mask where each original ROI is represented by a unique integer.
            The background is represented by 0, and each ROI gets a value from 1 to N.
            The output is a standard Mask with pixel type sitk.sitkLabelUInt8.

        Raises
        ------
        ValueError
            If the vector mask contains any overlapping regions (has_overlap() returns True).
            In this case, a lossless conversion to a label image is not possible.

        Notes
        -----
        This conversion preserves all information from the original vector mask only
        if there are no overlaps. The mapping between label values and original ROI names
        is preserved in the metadata.
        """

        return self._to_label_array(allow_overlap=False)

    def to_region_mask(
        self,
    ) -> Mask:
        """
        Encodes a VectorUInt8 image (with binary 0/1 components) into a single-channel
        image where each voxel value is a unique integer representing the bitmask
        of active components. Names are used in the lookup table.

        Parameters
        ----------
        vector_mask : sitk.Image
            A VectorUInt8 image where each component is 0 or 1.

        Returns
        -------
        Mask
        """
        n_components = self.GetNumberOfComponentsPerPixel()
        assert self.GetPixelID() == sitk.sitkVectorUInt8
        assert len(self.roi_mapping) == n_components + 1  # +1 for background

        if n_components <= 8:
            output_type = sitk.sitkUInt8
        elif n_components <= 16:
            output_type = sitk.sitkUInt16
        elif n_components <= 32:
            output_type = sitk.sitkUInt32
        else:
            raise TooManyComponentsError(n_components)

        label_image = sitk.Image(self.GetSize(), output_type)
        label_image.CopyInformation(self)

        for i in range(n_components):
            component = sitk.VectorIndexSelectionCast(
                self, i, outputPixelType=output_type
            )
            shifted = sitk.ShiftScale(component, shift=0, scale=2**i)
            label_image += shifted

        return Mask(label_image, metadata=self.metadata.copy())

    def extract_mask(self, key: str | int) -> Mask:
        """Extract a single binary mask by index or ROI key.

        Result would have a single label == 1 , output type is `sitk.sitkUInt8`.
        The mask is cached after first extraction for improved performance.

        Examples
        --------
        >>> roi_mapping = {
        ...     0: ROIMaskMapping("Background", ["bg"]),
        ...     1: ROIMaskMapping("Tumor", ["tumor"]),
        ...     2: ROIMaskMapping("Lung", ["lung"]),
        ... }
        >>> vector_mask = VectorMask(image, roi_mapping)
        >>> mask = vector_mask.extract_mask(1)
        # gets the mask for Tumor
        >>> mask = vector_mask.extract_mask("Lung")
        # gets the mask for Lung
        >>> mask = vector_mask.extract_mask(0)
        # gets the mask for Background
        """
        # Check if the mask is already in the cache
        if key in self._mask_cache:
            logger.debug(f"Cache hit for mask {key}")
            return self._mask_cache[key]

        mask_metadata = (
            self.metadata.copy()
        )  # Copy the metadata from vector mask

        match key:
            case int(idx) if idx > self.n_masks or idx < 0:
                msg = f"Index {idx} out of bounds for {self.n_masks=} masks."
                raise IndexError(msg)
            case int(0) | str("Background"):
                arr = sitk.GetArrayViewFromImage(self)
                # create binary image where background is 1 and all others are 0
                mask_image = sitk.GetImageFromArray(
                    (arr.sum(-1) == 0).astype(np.uint8)
                )

                # Update metadata with ROINames
                mask_metadata["ROINames"] = "Background"
            case int(idx):
                mask_image = sitk.VectorIndexSelectionCast(self, idx - 1)
                # Update metadata with ROINames if mapping exists
                mask_metadata["ROINames"] = "|".join(
                    self.roi_mapping[idx].roi_names
                )
            case str(key_str):
                if key_str not in self.roi_keys:
                    msg = f"Key '{key_str}' not found in mapping"
                    msg += f" {self.roi_mapping=}"
                    raise KeyError(msg)

                # note: background is bypassed here automatically!
                idx = self.roi_keys.index(key_str)
                mask_image = sitk.VectorIndexSelectionCast(self, idx)

                # Get the corresponding mapping entry and update ROINames
                mask_metadata["ROINames"] = "|".join(
                    self.roi_mapping[idx].roi_names
                )
            case _:
                msg = (
                    f"Invalid key type {type(key)=} where {key=}. "
                    "Expected int or str."
                )
                raise TypeError(msg)

        mask = Mask(
            mask_image,
            metadata=mask_metadata,
        )
        self._mask_cache[key] = mask
        return mask

    @classmethod
    def from_rtstruct(
        cls,
        reference_image: MedImage,
        rtstruct: RTStructureSet,  # StructureSet
        roi_matcher: ROIMatcher,
    ) -> VectorMask | None:
        """Create VectorMask from RTSTRUCT using ROI matching."""
        return rtstruct.get_vector_mask(
            reference_image=reference_image,
            roi_matcher=roi_matcher,
        )

    @classmethod
    def from_seg(
        cls,
        reference_image: MedImage,
        seg: SEG,
        roi_matcher: ROIMatcher,
    ) -> VectorMask | None:
        """Create VectorMask from SEG using ROI matching."""
        return seg.get_vector_mask(
            reference_image=reference_image,
            roi_matcher=roi_matcher,
        )

    def __rich_repr__(self):  # type: ignore[no-untyped-def] # noqa: ANN204
        yield "modality", self.metadata.get("Modality", "Unknown")
        yield from super().__rich_repr__()
        yield "roi_mapping", self.roi_mapping

    def __repr__(self) -> Any:  # type: ignore # noqa
        """Convert __rich_repr__ to a string representation."""
        parts = []
        for name, value in self.__rich_repr__():
            parts.append(f"{name}={value!r}")

        return f"<VectorMask {' '.join(parts)}>"


@dataclass
class Mask(MedImage):
    """A scalar label mask image with sitk.sitkUInt8 or sitk.sitkLabelUInt8 pixel type.

    This class represents 2D or 3D labeled mask images stored as SimpleITK scalar images.
    Each voxel contains a single integer label value, where:
        - 0 is conventionally reserved for background
        - Positive integers (1-255) represent different labels/segments

    The dimensionality (2D or 3D) is inherited from the source image data.

    Background handling:
        - Value 0 is always interpreted as background

    This class provides operations for handling labeled/segmentation data and converting
    between different representations.

    Attributes
    ----------
    metadata : dict[str, str]
        Dictionary containing metadata about the mask

    Notes
    -----
    - Multiple disjoint objects with the same label value are considered part
        of the same segment
    - To separate disjoint objects with the same label, where each has
        its own unique value use `to_labeled_image()`
    - When converting from label images to vector masks, each unique label
        becomes a separate channel
    """

    metadata: dict[str, str] = field(default_factory=dict)

    def __init__(
        self,
        image: sitk.Image,
        metadata: dict[str, str],
    ) -> None:
        """
        Parameters
        ----------
        image : sitk.Image
            A SimpleITK image with pixel type sitk.sitkUInt8 or sitk.sitkLabelUInt8
        metadata : dict[str, str]
            Dictionary containing metadata about the mask
        """
        super().__init__(image)
        self.metadata = metadata

    def __rich_repr__(self):  # type: ignore[no-untyped-def] # noqa: ANN204
        yield from super().__rich_repr__()
        if hasattr(self, "metadata") and self.metadata:
            yield "metadata", self.metadata

    def get_label_bounding_box(
        self,
    ) -> RegionBox:
        """Get bounding box around a label image for a given label or name.

        Returns
        -------
        RegionBox
            Bounding box around non-zero voxels in the label image.
            Contains min and max coordinates and size.
        """
        return RegionBox.from_mask_bbox(self, label=1)

    @property
    def fingerprint(self) -> dict[str, Any]:  # noqa: ANN001
        """Append to MedImage fingerprint"""
        bbox = self.get_label_bounding_box()
        return {
            **super().fingerprint,
            "bbox.size": bbox.size,
            "bbox.min_coord": bbox.min,
            "bbox.max_coord": bbox.max,
        }
