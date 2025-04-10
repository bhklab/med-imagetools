"""
Base class for extracting modality-specific DICOM metadata.

This module defines an extensible interface for building metadata extractors that
handle both simple DICOM tags and complex computed metadata fields, such as references
embedded in nested sequences.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, ClassVar

import pydicom

from imgtools.dicom import DicomInput, load_dicom
from imgtools.loggers import logger

if TYPE_CHECKING:
    from collections.abc import Mapping

ComputedValue = object | list[object]
"""Single value or list of values extracted from a DICOM dataset."""

ComputedField = Callable[[pydicom.Dataset], ComputedValue]
"""Function that extracts a value from a DICOM dataset"""

ExtractedFields = dict[str, ComputedValue]
"""Collection of computed values keyed by field name"""


class classproperty(property):  # noqa: N801
    """
    A decorator that behaves like @property, but on the class rather than instance.

    Useful for exposing computed class-level constants or derived metadata.
    """

    def __get__(self, _: Any, owner: type | None = None) -> Any:  # noqa: ANN401
        if owner is None:
            owner = type(self)
        return self.fget(owner)  # type: ignore


class ModalityMetadataExtractor(ABC):
    """
    Abstract base class for modality-specific DICOM metadata extractors.

    This class supports both standard DICOM tag retrieval and more complex field
    computations based on the full DICOM dataset. Subclasses must specify the modality
    they support and define additional metadata fields either as DICOM tag names
    or as custom computation functions.

    Attributes
    ----------
    base_tags : ClassVar[set[str]]
        Standard DICOM tags to always extract, regardless of modality.
    modality_tags : ClassVar[set[str]]
        Tags specific to the subclass's modality. These are merged with `base_tags`
        to form the list of tags to retrieve directly from the dataset.
    computed_fields : ClassVar[Mapping[str, ComputedField]]
        A mapping of metadata field names to callables that compute values from
        the loaded `pydicom.Dataset`.

    Methods
    -------
    metadata_keys() : list[str]
        Returns a predictable, sorted list of all metadata field names
        produced by this extractor.
    extract(dicom: DicomInput) : dict[str, ComputedValue]
        Extracts metadata tags and computed fields from a DICOM dataset.
        Returns a dictionary mapping metadata field names to values.

    Notes
    -----
    Subclasses MUST implement the following abstract methods/properties:
    - `modality() -> str`: A class method that returns the DICOM modality string handled
      (e.g., "CT", "MR", "RTDOSE").
    - `modality_tags -> set[str]`: A class property that defines the set of DICOM attribute
      names (tags) specific to the modality.
    - `computed_fields -> Mapping[str, Callable[[pydicom.Dataset], ComputedValue]]`: A class property
      that defines a mapping of metadata field names to callables which compute their values.

    Examples
    --------
    >>> class CTExtractor(ModalityMetadataExtractor):
    >>>     @classmethod
    >>>     def modality(cls) -> str:
    >>>         return "CT"
    >>>     @classproperty
    >>>     def modality_tags(cls) -> set[str]:
    >>>         return {"KVP", "ReconstructionAlgorithm"}
    >>>     @classproperty
    >>>     def computed_fields(cls) -> Mapping[str, ComputedField]:
    >>>         return {
    >>>             "CustomValue": lambda ds: str(float(ds.SliceThickness) * 2),
    >>>             "DoublePatientAge": lambda ds: str(ds.PatientAge * 2)
    >>>         }

    >>> # Using the extractor
    >>> metadata = CTExtractor.extract("file.dcm")
    >>> # Returns: {'PatientID': '123', 'KVP': '120', 'CustomValue': '5.0', ...}
    """

    base_tags: ClassVar[set[str]] = {
        # Patient Information
        "PatientID",
        "SeriesInstanceUID",
        "StudyInstanceUID",
        "Modality",
        # Image Geometry & Size
        "BodyPartExamined",
        "DataCollectionDiameter",
        "FrameOfReferenceUID",
        "NumberOfSlices",
        "SliceThickness",
        "PatientPosition",
        "PixelSpacing",
        "ImageOrientationPatient",
        "ImagePositionPatient",
        "SpacingBetweenSlices",
        # Image Processing & Rescaling
        "RescaleType",
        "RescaleSlope",
        "RescaleIntercept",
        # Scanner & Manufacturer Information
        "Manufacturer",
        "ManufacturerModelName",
        "DeviceSerialNumber",
        "SoftwareVersions",
        "InstitutionName",
        "StationName",
        # Image Acquisition Parameters
        "ScanType",
        "ScanProgressionDirection",
        "ScanOptions",
        "AcquisitionNumber",
        "ProtocolName",
        # Date Time Information
        "StudyDate",
        "StudyTime",
        "SeriesDate",
        "SeriesTime",
        "ContentDate",
        "ContentTime",
        "AcquisitionDate",
        "AcquisitionTime",
        "InstanceCreationDate",
        "InstanceCreationTime",
    }

    @classmethod
    @abstractmethod
    def modality(cls) -> str:
        """
        The DICOM modality handled by this extractor (e.g., "CT", "MR").

        Returns
        -------
        str
            Modality name.
        """
        pass

    @classproperty
    @abstractmethod
    def modality_tags(cls) -> set[str]:  # noqa: N805
        """
        A set of DICOM tags specific to the modality handled by this extractor.

        Returns
        -------
        set[str]
            Set of DICOM tag names.
        """
        pass

    @classproperty
    @abstractmethod
    def computed_fields(cls) -> Mapping[str, ComputedField]:  # noqa: N805
        """
        A mapping of metadata field names to callables that compute their values.

        The callable should accept a pydicom Dataset and return a value.

        Returns
        -------
        dict[str, Callable[[pydicom.Dataset], ComputedValue]]
            Mapping of field names to computation functions.
        """
        pass

    @classmethod
    def metadata_keys(cls) -> list[str]:
        """
        Return a predictable, sorted list of metadata field names.

        This includes both direct DICOM tag names and any computed metadata keys.

        Returns
        -------
        list[str]
            All metadata keys produced by this extractor.
        """
        # if no modality_tags or computed_fields are defined, return base_tags
        if not cls.modality_tags and not cls.computed_fields:
            return sorted(cls.base_tags)

        all_tags = cls.base_tags.union(cls.modality_tags)
        all_keys = all_tags.union(cls.computed_fields.keys())
        return sorted(all_keys)

    @classmethod
    def extract(
        cls, dicom: DicomInput, extra_tags: list[str] | None = None
    ) -> ExtractedFields:
        """
        Extract metadata tags and computed fields from a DICOM dataset.

        Parameters
        ----------
        dicom : DicomInput
            A path, byte stream, or pydicom FileDataset.
        extra_tags : list[str] | None, optional
            Additional DICOM tags to extract, by default None

        Returns
        -------
        dict[str, ComputedValue]
            A dictionary mapping metadata field names to values.
            Values may be strings, numbers, dictionaries, or lists of these types.
            Missing tags or errors during computation will result in an empty string.

        Notes
        -----
        Be aware that using extra_tags may lead to unexpected results if the
        extra tags are not compatible with the modality or if they are not
        present in the DICOM file. The extractor will not validate the extra tags
        against the modality, so it's the user's responsibility to ensure that
        the extra tags are relevant and valid for the given DICOM file.
        """
        ds = load_dicom(dicom)
        output: ExtractedFields = {}

        # Extract base and modality-specific tags
        tags_to_extract = cls.base_tags.union(cls.modality_tags)
        if extra_tags:
            tags_to_extract = tags_to_extract.union(extra_tags)

        for tag in tags_to_extract:
            output[tag] = str(ds.get(tag, ""))

        # Compute advanced fields
        for key, fn in cls.computed_fields.items():
            try:
                # Store computed value directly without conversion to string
                output[key] = fn(ds)
            except Exception as e:
                warnmsg = (
                    f"Failed to compute field '{key}' for modality '{cls.modality()}'. "
                    "This may be due to missing or malformed data in the DICOM file."
                )
                warnmsg += f" Error: {e}"
                logger.warning(warnmsg, file=str(dicom))
                output[key] = ""

        # sort all keys
        return {k: output[k] for k in sorted(output.keys())}
