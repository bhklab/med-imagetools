from pathlib import Path

# Import needed for type hints
from typing import TYPE_CHECKING, Any, Optional, Union

import SimpleITK as sitk

from imgtools.dicom.dicom_metadata import extract_metadata
from imgtools.utils import (
    attrify,
    cleanse_metadata,
    convert_dictionary_datetime_values,
)

if TYPE_CHECKING:
    from imgtools.coretypes import (
        SEG,
        MedImage,
        RTStructureSet,
    )
# Type for dispatch functions return values
MedImageT = Union["MedImage", "RTStructureSet", "SEG"]


def read_dicom_series(
    path: str,
    series_id: str | None = None,
    recursive: bool = False,
    file_names: list[str] | None = None,
    **kwargs: Any,  # noqa
) -> tuple[sitk.Image, dict]:
    """Read DICOM series as SimpleITK Image.

    Parameters
    ----------
    path
       Path to directory containing the DICOM series.

    recursive, default=False
       Whether to recursively parse the input directory when searching for
       DICOM series,

    series_id, default=None
       Specifies the DICOM series to load if multiple series are present in
       the directory. If None and multiple series are present, loads the first
       series found.

    file_names, default=None
        If there are multiple acquisitions/"subseries" for an individual series,
        use the provided list of file_names to set the ImageSeriesReader.

    Returns
    -------
    image
        SimpleITK Image object containing the DICOM series.
    metadata
        Dictionary containing metadata extracted from one file in the series.
    """
    reader = sitk.ImageSeriesReader()
    sitk_file_names = reader.GetGDCMSeriesFileNames(
        path,
        seriesID=series_id if series_id else "",
        recursive=recursive,
    )
    if file_names is None:
        file_names = sitk_file_names
    elif set(file_names) <= set(
        sitk_file_names
    ):  # Extracts the same order provided by sitk
        file_names = [fn for fn in sitk_file_names if fn in file_names]
    else:
        errmsg = (
            "The provided file_names are not a subset of the files in the "
            "directory."
        )
        errmsg += f"\nProvided file_names: {file_names}"
        errmsg += f"\n\nFiles in directory: {sitk_file_names}"
        raise ValueError(errmsg)

    reader.SetFileNames(file_names)

    metadata = kwargs.pop("metadata", None)

    if not metadata:
        # Extract metadata from the first file
        metadata = extract_metadata(file_names[0])
    # make sure its a dictionary
    elif not isinstance(metadata, dict):
        raise ValueError("metadata must be a dictionary")

    metadata = cleanse_metadata(metadata)
    metadata = convert_dictionary_datetime_values(metadata)
    metadata = attrify(metadata)
    return reader.Execute(), metadata


def read_dicom_auto(
    path: str,
    modality: Optional[str] = None,
    **kwargs: Any,  # noqa
) -> MedImageT:
    """General DICOM reader that dispatches to the correct class based on modality.

    This function automatically determines the appropriate class based on the
    modality and calls its from_dicom method with the provided arguments.

    Parameters
    ----------
    path : str
        Path to the DICOM file or directory containing DICOM files.
    modality : str, optional
        Explicitly specify the modality. If None, the function will try to determine
        the modality from the DICOM metadata.
    **kwargs : Any
        Additional keyword arguments to pass to the specific from_dicom method.
        Common parameters include:
            - series_id: str | None - Series ID for DICOM series
            - recursive: bool - Whether to search recursively for DICOM files
            - file_names: list[str] | None - Specific file names to read
            - pet_image_type: For PET images, specify SUV or ACT

    Returns
    -------
    MedImageT
        The loaded image or mask object of the appropriate type.

    Raises
    ------
    ValueError
        If the modality is unknown or cannot be determined.
    ImportError
        If the required class for a modality cannot be imported.
    """
    from pydicom import dcmread

    from imgtools.dicom import find_dicoms

    # Try to determine modality if not provided
    if not modality:
        # If it's a directory with DICOM files, read the first file
        path_obj = Path(path)
        if path_obj.is_dir():
            first_file = find_dicoms(
                directory=path_obj,
                recursive=kwargs.pop("recursive", False),
                limit=1,
            )
            if not first_file:
                errmsg = (
                    f"No DICOM files found in directory: {path_obj}. "
                    "Please check the path and try again."
                )
                raise FileNotFoundError(errmsg)
            # find_dicoms returns a list, even if limit=1
            dcm = dcmread(first_file[0], stop_before_pixels=True)
        else:
            # It's a file
            dcm = dcmread(path, stop_before_pixels=True)

        # Extract modality from the DICOM header
        modality = getattr(dcm, "Modality", None)
        if not modality:
            raise ValueError(
                "Could not determine modality from DICOM file. Please specify modality parameter."
            )
            # Dispatch based on modality

    match modality:
        case "CT" | "MR":
            from imgtools.coretypes import Scan

            return Scan.from_dicom(path, **kwargs)
        case "PT":
            from imgtools.coretypes import PET

            return PET.from_dicom(path, **kwargs)
        case "RTDOSE":
            from imgtools.coretypes import Dose

            return Dose.from_dicom(path, **kwargs)
        case "RTSTRUCT":
            from imgtools.coretypes import RTStructureSet

            return RTStructureSet.from_dicom(path)
        case "SEG":
            from imgtools.coretypes import SEG

            return SEG.from_dicom(path)
        case _:
            error_msg = f"Unknown or unsupported modality: {modality}"
            raise ValueError(error_msg)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Read DICOM files.")
    parser.add_argument(
        "path", type=str, help="Path to DICOM file or directory"
    )
    parser.add_argument(
        "--modality", type=str, help="Modality to use for reading DICOM files"
    )
    args = parser.parse_args()
    from rich import print  # noqa: A004

    print(read_dicom_auto(args.path, args.modality))
