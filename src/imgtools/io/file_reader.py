from pathlib import Path

import itk
import SimpleITK as sitk
from pydicom import FileDataset

from imgtools.dicom.input.dicom_reader import (
    DicomInput,
    load_dicom,
    path_from_pathlike,
)

# alias this
read_dicom = load_dicom
"""Alias for :func:`imgtools.dicom.input.load_dicom`."""


def read_scan(
    directory_input: Path,
    series_uid: str,
    recursive: bool = False,
) -> sitk.Image:
    reader = sitk.ImageSeriesReader()

    dicom_names = reader.GetGDCMSeriesFileNames(
        str(directory_input), series_uid
    )

    """
    if its a single file, 
        

    """

    raise NotImplementedError("This function is not yet implemented")


def read_sitk(read_input: Path | list[Path]) -> sitk.Image:
    """Read an image from the specified file path using SimpleITK

    Returns
    -------
    sitk.Image
        The image read from the file.
    """

    match read_input:
        case Path() as one_path:
            return sitk.ReadImage(str(one_path.as_posix()))
        case [*multiple_paths]:
            return sitk.ReadImage(
                [str(path.as_posix()) for path in multiple_paths]
            )
        case _:
            raise TypeError("Input must be a Path or a list of Paths")
