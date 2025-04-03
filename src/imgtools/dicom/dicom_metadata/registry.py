from typing import Type

from imgtools.dicom.dicom_metadata.extractor_base import (
    ModalityMetadataExtractor,
)

# Internal registry mapping modality → extractor class
_EXTRACTOR_REGISTRY: dict[str, Type[ModalityMetadataExtractor]] = {}


def register_extractor(
    cls: Type[ModalityMetadataExtractor],
) -> Type[ModalityMetadataExtractor]:
    """
    Register a modality extractor class in the global registry.

    Parameters
    ----------
    cls : Type[ModalityMetadataExtractor]
        The subclass to register.

    Returns
    -------
    Type[ModalityMetadataExtractor]
        The class itself (unchanged), for use as a decorator.
    """
    modality = cls.modality()
    if modality in _EXTRACTOR_REGISTRY:
        msg = (
            f"Modality '{modality}' already"
            f"registered by {_EXTRACTOR_REGISTRY[modality].__name__}"
        )
        raise ValueError(msg)
    _EXTRACTOR_REGISTRY[modality] = cls
    return cls


def get_extractor(modality: str) -> Type[ModalityMetadataExtractor]:
    """
    Retrieve a registered extractor for the given modality.

    Parameters
    ----------
    modality : str
        The DICOM modality string (e.g., "CT", "MR").

    Returns
    -------
    Type[ModalityMetadataExtractor]
        The corresponding registered extractor class.

    Raises
    ------
    KeyError
        If no extractor is registered for the modality.
    """
    return _EXTRACTOR_REGISTRY[modality]


def supported_modalities() -> list[str]:
    """
    List all registered modalities.

    Returns
    -------
    list[str]
        Sorted list of supported modality names.
    """
    return sorted(_EXTRACTOR_REGISTRY.keys())
