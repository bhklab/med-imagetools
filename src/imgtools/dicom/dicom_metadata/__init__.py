"""
dicom_metadata: DICOM modality-based metadata extraction framework.
"""

# ruff: noqa
from imgtools.dicom import DicomInput, load_dicom

from .registry import (
    get_extractor,
    register_extractor,
    supported_modalities,
    ExistingExtractorError,
)

# need to do this to register all extractors during runtime
from . import extractors
from .extractor_base import ComputedValue

__all__ = [
    "get_extractor",
    "register_extractor",
    "supported_modalities",
    "extract_metadata",
    "get_keys_from_modality",
    "ExistingExtractorError",
]


def extract_metadata(
    dicom: DicomInput,
    modality: str | None = None,
    extra_tags: list[str] | None = None,
) -> dict[str, ComputedValue]:
    """
    Extract metadata from a DICOM file based on its modality.

    Parameters
    ----------
    dicom : DicomInput
        DICOM input source (path, bytes, or pydicom Dataset)
    modality : str | None, optional
        Explicitly specify the modality to use, by default None.
        If None, the modality is extracted from the DICOM file.
    extra_tags : list[str] | None, optional
        Additional DICOM tags to extract, by default None.
        If None, no extra tags are extracted.

    Returns
    -------
    dict[str, ComputedValue]
        Dictionary of metadata fields with their values extracted from the DICOM.

    Raises
    ------
    ValueError
        If no modality can be determined.

    Notes
    -----
    Be aware that using extra_tags may lead to unexpected results if the
    extra tags are not compatible with the modality or if they are not
    present in the DICOM file. The extractor will not validate the extra tags
    against the modality, so it's the user's responsibility to ensure that
    the extra tags are relevant and valid for the given DICOM file.
    """
    ds = load_dicom(dicom)
    modality = modality or ds.get("Modality")
    if not modality:
        raise ValueError("No modality found in DICOM")

    extractor_cls = get_extractor(modality)
    return extractor_cls.extract(ds, extra_tags=extra_tags)


def get_keys_from_modality(modality: str) -> list[str]:
    """
    Get the keys for a given modality.
    """
    extractor_cls = get_extractor(modality)
    return extractor_cls.metadata_keys()
