from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Sequence

from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    field_validator,
)

from imgtools.coretypes import MedImage, VectorMask
from imgtools.io.validators import validate_directory
from imgtools.io.writers import (
    AbstractBaseWriter,
    ExistingFileMode,
    NIFTIWriter,
)
from imgtools.loggers import logger

DEFAULT_FILENAME_FORMAT = "{SampleNumber}__{PatientID}/{Modality}_{SeriesInstanceUID}/{ImageID}.nii.gz"

__all__ = ["SampleOutput", "AnnotatedPathSequence"]


class FailedToSaveSingleImageError(Exception):
    """Exception raised when a single image fails to save."""

    def __init__(self, message: str, image: MedImage) -> None:
        super().__init__(message)
        self.image = image


class AnnotatedPathSequence(list):
    """
    Custom sequence of paths that behaves like a list but includes an errors attribute.

    This class is returned by SampleOutput.__call__ to allow access to any errors
    that occurred during the save process while still behaving like a regular
    sequence of paths.

    Attributes
    ----------
    errors : List[FailedToSaveSingleImageError]
        List of errors that occurred during the save process.
    """

    errors: List[FailedToSaveSingleImageError] | None

    def __init__(
        self,
        paths: List[Path],
        errors: List[FailedToSaveSingleImageError] | None = None,
    ) -> None:
        """
        Initialize the annotated path sequence.

        Parameters
        ----------
        paths : List[Path]
            List of paths to saved files.
        errors : List[FailedToSaveSingleImageError], optional
            List of errors that occurred during the save process.
        """
        super().__init__(paths)
        self.errors = errors or []

    def __repr__(self) -> str:
        """Return a string representation of the object."""
        paths_repr = super().__repr__()
        if not self.errors:
            return paths_repr
        return f"{paths_repr} (with {len(self.errors)} errors)"


class SampleOutput(BaseModel):
    """
    Configuration model for saving medical imaging outputs.

    This class provides a standardized configuration for saving medical images,
    supporting various file formats and output organization strategies.

    Attributes
    ----------
    directory : Path
        Directory where output files will be saved. Must exist and be writable.
    filename_format : str
        Format string for output filenames with placeholders for metadata values.
    existing_file_mode : ExistingFileMode
        How to handle existing files (FAIL, SKIP, OVERWRITE).
    extra_context : Dict[str, Any]
        Additional metadata to include when saving files.

    Examples
    --------
    >>> from imgtools.io import SampleOutput
    >>> from imgtools.io.writers import ExistingFileMode
    >>> output = SampleOutput(
    ...     directory="results/patient_scans",
    ...     filename_format="{PatientID}/{Modality}/{ImageID}.nii.gz",
    ...     existing_file_mode=ExistingFileMode.SKIP,
    ... )
    >>> output(scan_list)  # Save all scans in the list
    """

    directory: Path = Field(
        description="Path where output files will be saved. Absolute path or relative to the current working directory.",
        title="Output Directory",
        examples=["output/processed_scans", "/absolute/path/to/output"],
    )
    filename_format: str = Field(
        default=DEFAULT_FILENAME_FORMAT,
        description="Format string for output filenames with placeholders for metadata values. Available fields depend on the metadata in the images being saved.",
        title="Filename Format",
        examples=[
            "{PatientID}/{Modality}/{ImageID}.nii.gz",
            "{PatientID}/roi_{roi_key}.nii.gz",
        ],
    )
    existing_file_mode: ExistingFileMode = Field(
        ExistingFileMode.FAIL,
        description="How to handle existing files: FAIL (raise error), SKIP (don't overwrite), or OVERWRITE (replace existing files).",
        title="Existing File Handling",
    )
    extra_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata fields to include when saving files. These values can be referenced in the filename_format.",
        title="Extra Metadata",
        examples=[
            {"dataset": "NSCLC-Radiomics", "processing_date": "2025-04-22"}
        ],
    )

    _writer: AbstractBaseWriter | None = PrivateAttr(default=None)

    def model_post_init(self, __context) -> None:  # type: ignore # noqa: ANN001
        """Initialize the writer after model initialization."""
        self._writer = NIFTIWriter(
            root_directory=self.directory,
            existing_file_mode=self.existing_file_mode,
            filename_format=self.filename_format,
            context=self.extra_context,
        )

    @field_validator("directory")
    @classmethod
    def validate_directory(cls, v: str | Path) -> Path:
        """Validate that the output directory exists or can be created, and is writable."""
        return validate_directory(v, create=True)

    @classmethod
    def default(cls) -> SampleOutput:
        """Create a default instance of SampleOutput."""
        return cls(
            directory=Path("output"),
            filename_format=DEFAULT_FILENAME_FORMAT,
            existing_file_mode=ExistingFileMode.FAIL,
            extra_context={},
        )

    @property
    def writer(self) -> AbstractBaseWriter:
        """Get the writer instance."""
        if self._writer is None:
            raise ValueError("Writer is not initialized.")
        return self._writer

    def __call__(
        self, data: Sequence[MedImage], /, **kwargs: object
    ) -> AnnotatedPathSequence:
        """
        Save the data to files using the configured writer.

        Parameters
        ----------
        data : List[MedImage]
            List of medical images to save.
        **kwargs
            Additional metadata to include when saving.

        Returns
        -------
        AnnotatedPathSequence
            List of paths to the saved files, annotated with any errors that occurred.
        """
        saved_files = []
        save_errors = []
        for image in data:
            try:
                if isinstance(image, VectorMask):
                    for (
                        _i,
                        roi_key,
                        roi_names,
                        image_id,
                        mask,
                    ) in image.iter_masks():
                        # image_id = f"{roi_key}_[{matched_rois}]"
                        p = self.writer.save(
                            mask,
                            roi_key=roi_key,
                            matched_rois="|".join(roi_names),
                            **image.metadata,
                            **kwargs,
                            ImageID=image_id,
                        )
                        saved_files.append(p)
                elif isinstance(image, MedImage):
                    # Handle MedImage case
                    p = self.writer.save(
                        image,
                        **image.metadata,
                        **kwargs,
                        ImageID=image.metadata["Modality"],
                    )
                    saved_files.append(p)
                else:
                    errmsg = (
                        f"Unsupported image type: {type(image)}. "
                        "Expected MedImage or VectorMask."
                    )
                    logger.error(errmsg)
                    raise TypeError(errmsg)
            except Exception as e:
                errmsg = f"Failed to save image SeriesUID: {image.metadata['SeriesInstanceUID']}: {e}"

                # create an error object
                save_error = FailedToSaveSingleImageError(errmsg, image)
                save_errors.append(save_error)
                logger.error(errmsg, error=save_error)

        return AnnotatedPathSequence(saved_files, save_errors)
