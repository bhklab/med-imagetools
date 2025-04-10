from typing import Any

import SimpleITK as sitk

from imgtools.dicom.dicom_metadata import extract_metadata


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

    recursive, optional
       Whether to recursively parse the input directory when searching for
       DICOM series,

    series_id, optional
       Specifies the DICOM series to load if multiple series are present in
       the directory. If None and multiple series are present, loads the first
       series found.

    file_names, optional
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

    return reader.Execute(), metadata
