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

__all__ = [
    "get_extractor",
    "register_extractor",
    "supported_modalities",
    "extract_metadata",
]


def extract_metadata(
    dicom: DicomInput, modality: str | None = None
) -> dict[str, str]:
    ds = load_dicom(dicom)
    modality = modality or ds.get("Modality")
    if not modality:
        raise ValueError("No modality found in DICOM")

    extractor_cls = get_extractor(modality)
    return extractor_cls.extract(ds)
