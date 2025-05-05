from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

import numpy as np
import SimpleITK as sitk

from imgtools.coretypes import MedImage
from imgtools.loggers import logger
from imgtools.utils import truncate_uid

from .abstract_base_writer import AbstractBaseWriter, ExistingFileMode


class NiftiWriterError(Exception):
    """Base exception for NiftiWriter errors."""

    pass


class NiftiWriterValidationError(NiftiWriterError):
    """Raised when validation of writer configuration fails."""

    pass


class NiftiWriterIOError(NiftiWriterError):
    """Raised when I/O operations fail."""

    pass


@dataclass
class NIFTIWriter(AbstractBaseWriter[sitk.Image | np.ndarray]):
    """Class for managing file writing with customizable paths and filenames for NIFTI files.

    This class extends the AbstractBaseWriter to provide specialized functionality
    for writing NIFTI image files. It supports both SimpleITK Image objects and numpy arrays
    as input data types.

    Attributes
    ----------
    compression_level : int, default=9
        Compression level (0-9). Higher means better compression but slower writing.
        Value must be between MIN_COMPRESSION_LEVEL (0) and MAX_COMPRESSION_LEVEL (9).
    truncate_uids_in_filename : int, default=8
        Many DICOM files have long UIDs in the filename. If used in the filename format,
        this will truncate the UID to the **last** `truncate_uids_in_filename`
        characters.
        A value of 0 means **no truncation**.
    VALID_EXTENSIONS : ClassVar[list[str]]
        List of valid file extensions for NIFTI files (".nii", ".nii.gz").
    MAX_COMPRESSION_LEVEL : ClassVar[int]
        Maximum allowed compression level (9).
    MIN_COMPRESSION_LEVEL : ClassVar[int]
        Minimum allowed compression level (0).

    Inherited Attributes
    -------------------
    root_directory : Path
        Root directory where files will be saved. This directory will be created
        if it doesn't exist and `create_dirs` is True.
    filename_format : str
        Format string defining the directory and filename structure.
        Supports placeholders for context variables enclosed in curly braces.
        Example: '{subject_id}_{date}/{disease}.nii.gz'
    create_dirs : bool, default=True
        Creates necessary directories if they don't exist.
    existing_file_mode : ExistingFileMode, default=ExistingFileMode.FAIL
        Behavior when a file already exists.
        Options: OVERWRITE, SKIP, FAIL
    sanitize_filenames : bool, default=True
        Replaces illegal characters from filenames with underscores.
    context : Dict[str, Any], default={}
        Internal context storage for pre-checking.
    index_filename : Optional[str], default=None
        Name of the index file to track saved files.
        If an absolute path is provided, it will be used as is.
        If not provided, it will be saved in the root directory with the format
        of {root_directory.name}_index.csv.
    overwrite_index : bool, default=False
        Overwrites the index file if it already exists.
    absolute_paths_in_index : bool, default=False
        If True, saves absolute paths in the index file.
        If False, saves paths relative to the root directory.
    pattern_resolver : PatternResolver
        Instance used to handle filename formatting with placeholders.

    Notes
    -----
    When using this class, ensure your filename_format ends with one of the VALID_EXTENSIONS.
    The class validates the compression level and filename format during initialization.
    """

    compression_level: int = field(default=9)
    truncate_uids_in_filename: int = field(default=8)

    # Make extensions immutable
    VALID_EXTENSIONS: ClassVar[list[str]] = [
        ".nii",
        ".nii.gz",
    ]
    MAX_COMPRESSION_LEVEL: ClassVar[int] = 9
    MIN_COMPRESSION_LEVEL: ClassVar[int] = 0

    def __post_init__(self) -> None:
        """Validate writer.

        Parent class will create the output directory, validate filename pattern, and update
        ExtingFileMode if necessary.
        """
        super().__post_init__()

        if (
            not self.MIN_COMPRESSION_LEVEL
            <= self.compression_level
            <= self.MAX_COMPRESSION_LEVEL
        ):
            msg = (
                f"Invalid compression level {self.compression_level}. "
                f"Must be between {self.MIN_COMPRESSION_LEVEL} and "
                f"{self.MAX_COMPRESSION_LEVEL}."
            )
            raise NiftiWriterValidationError(msg)

        if not any(
            self.filename_format.endswith(ext) for ext in self.VALID_EXTENSIONS
        ):
            msg = (
                f"Invalid filename format {self.filename_format}. "
                f"Must end with one of {self.VALID_EXTENSIONS}."
            )
            raise NiftiWriterValidationError(msg)

    def save(self, data: sitk.Image | np.ndarray, **kwargs: object) -> Path:
        """Write the SimpleITK image to a NIFTI file.

        Parameters
        ----------
        data : sitk.Image | np.ndarray
            The SimpleITK image or numpy array to save
        **kwargs : object
            Additional formatting parameters for the output path

        Returns
        -------
        Path
            Path to the saved file

        Raises
        ------
        NiftiWriterIOError
            If writing fails
        NiftiWriterValidationError
            If the input data is invalid
        """
        match data:
            case sitk.Image():
                image = data
            case np.ndarray():
                image = sitk.GetImageFromArray(data)
            case _:
                msg = "Input must be a SimpleITK Image or a numpy array"
                raise NiftiWriterValidationError(msg)

        # if the object has the 'fingerprint' property, update the context
        if hasattr(data, "serialized_fingerprint"):
            self.set_context(**data.serialized_fingerprint)
        elif isinstance(data, MedImage):
            # if there is no fingerprint, this is unexpected
            # this is an issue now since we auto keep context between
            # saves, so this could lead to using the fingerprint
            # of the previous save
            logger.error(
                "No fingerprint found in the writer object. "
                "This is unexpected and may indicate a bug. "
                "The fingerprint fields in the index might be incorrect."
            )
            # TODO:: think of a better way to handle this
            self.clear_context()

        # TODO:: think of a better way to handle the truncate_uids_in_filename
        if self.truncate_uids_in_filename:
            truncated_kwargs = {
                k: truncate_uid(str(v), self.truncate_uids_in_filename)
                if k.lower().endswith("uid")
                else v
                for k, v in kwargs.items()
            }
            out_path = self.resolve_path(**truncated_kwargs)
            # need to update the context with the old kwargs
            # because it will be used in the index, and we dont want
            # to truncate the UIDs in the index
            self.set_context(**kwargs)
        else:
            out_path = self.resolve_path(**kwargs)

        if (
            out_path.exists()  # check if it exists
            # This will only be true if SKIP,
            # OVERWRITE would have deleted the file
            and self.existing_file_mode == ExistingFileMode.SKIP
        ):
            logger.debug("File exists, skipping.", out_path=out_path)
            return out_path

        try:
            sitk.WriteImage(
                image,
                out_path.as_posix(),
                useCompression=True,
                compressionLevel=self.compression_level,
            )
        except Exception as e:
            msg = f"Error writing image to file {out_path}: {e}"
            raise NiftiWriterIOError(msg) from e

        self.add_to_index(
            out_path,
            filepath_column="filepath",
            replace_existing=out_path.exists(),
        )

        return out_path
