from typing import Type

from imgtools.dicom.dicom_metadata.extractor_base import (
    ModalityMetadataExtractor,
)

# Internal registry mapping modality → extractor class
_EXTRACTOR_REGISTRY: dict[str, Type[ModalityMetadataExtractor]] = {}


class ExistingExtractorError(Exception):
    """
    Exception raised when trying to register an extractor for
    an already registered modality.
    """

    def __init__(
        self,
        modality: str,
        existing_extractor: Type[ModalityMetadataExtractor],
    ) -> None:
        self.modality = modality
        self.existing_extractor = existing_extractor
        super().__init__(
            f"Modality '{modality}' already registered by {existing_extractor.__name__}"
        )


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
    modality = cls.modality().upper()
    if modality in _EXTRACTOR_REGISTRY:
        raise ExistingExtractorError(modality, _EXTRACTOR_REGISTRY[modality])
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
        If no extractor is registered for the modality, returns a FallbackMetadataExtractor.
    """
    x = _EXTRACTOR_REGISTRY.get(modality.upper(), None)
    if not x:
        from imgtools.dicom.dicom_metadata.extractors import (
            FallbackMetadataExtractor,
        )

        x = FallbackMetadataExtractor
    return x


def supported_modalities() -> list[str]:
    """
    List all registered modalities.

    Returns
    -------
    list[str]
        Sorted list of supported modality names.
    """
    return sorted(_EXTRACTOR_REGISTRY.keys())
