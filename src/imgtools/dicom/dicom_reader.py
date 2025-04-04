import os
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO, TypeAlias, cast

from pydicom import dcmread
from pydicom.dataset import FileDataset

from imgtools.exceptions import (
    InvalidDicomError,
)

# Define a type alias for DICOM input types
DicomInput: TypeAlias = FileDataset | str | Path | bytes | BinaryIO


def path_from_pathlike(file_object: str | Path | BinaryIO) -> str | BinaryIO:
    """Return the string representation if file_object is path-like,
    otherwise return the object itself.

    Parameters
    ----------
    file_object : str | Path | BinaryIO
        File path or file-like object.

    Returns
    -------
    str | BinaryIO
        String representation of the path or the original file-like object.
    """
    try:
        return os.fspath(file_object)  # type: ignore[arg-type]
    except TypeError:
        return cast("BinaryIO", file_object)


def load_dicom(
    dicom_input: DicomInput,
    force: bool = True,
    stop_before_pixels: bool = True,
    **kwargs: Any,  # noqa: ANN401
) -> FileDataset:
    """Load a DICOM file and return the parsed FileDataset object.

    This function supports various input types including file paths, byte streams,
    and file-like objects. It uses the `pydicom.dcmread` function to read the DICOM file.

    Notes
    -----
    - If `dicom_input` is already a `FileDataset`, it is returned as is.
    - If `dicom_input` is a file path or file-like object, it is read using `pydicom.dcmread`.
    - If `dicom_input` is a byte stream, it is wrapped in a `BytesIO` object and then read.
    - An `InvalidDicomError` is raised if the input type is unsupported.

    Parameters
    ----------
    dicom_input : FileDataset | str | Path | bytes | BinaryIO
        Input DICOM file as a `pydicom.FileDataset`, file path, byte stream, or file-like object.
    force : bool, optional
        Whether to allow reading DICOM files missing the *File Meta Information*
        header, by default True.
    stop_before_pixels : bool, optional
        Whether to stop reading the DICOM file before loading pixel data, by default True.
    **kwargs
        Additional keyword arguments to pass to `pydicom.dcmread`.
        i.e `specific_tags`.
    Returns
    -------
    FileDataset
        Parsed DICOM dataset.

    Raises
    ------
    InvalidDicomError
        If the input is of an unsupported type or cannot be read as a DICOM file.
    """
    match dicom_input:
        case FileDataset():
            return dicom_input
        case str() | Path() | BinaryIO():
            dicom_source = path_from_pathlike(dicom_input)
            return dcmread(
                dicom_source,
                force=force,
                stop_before_pixels=stop_before_pixels,
                **kwargs,
            )
        case bytes():
            return dcmread(
                BytesIO(dicom_input),
                force=force,
                stop_before_pixels=stop_before_pixels,
                **kwargs,
            )
        case _:
            msg = (
                f"Invalid input type for 'dicom_input': {type(dicom_input)}. "
                "Must be a FileDataset, str, Path, bytes, or BinaryIO object."
            )
            raise InvalidDicomError(msg)
