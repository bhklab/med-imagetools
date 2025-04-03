"""
dicom_metadata: DICOM modality-based metadata extraction framework.
"""

# ruff: noqa
from imgtools.dicom import DicomInput, load_dicom

from .registry import (
    get_extractor,
    register_extractor,
    supported_modalities,
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
]


def extract_metadata(
    dicom: DicomInput, modality: str | None = None
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

    Returns
    -------
    dict[str, ComputedValue]
        Dictionary of metadata fields with their values extracted from the DICOM.

    Raises
    ------
    ValueError
        If no modality can be determined.
    """
    ds = load_dicom(dicom)
    modality = modality or ds.get("Modality")
    if not modality:
        raise ValueError("No modality found in DICOM")

    extractor_cls = get_extractor(modality)
    return extractor_cls.extract(ds)


def get_keys_from_modality(modality: str) -> list[str]:
    """
    Get the keys for a given modality.
    """
    extractor_cls = get_extractor(modality)
    return extractor_cls.metadata_keys()
