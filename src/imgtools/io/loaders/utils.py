from __future__ import annotations

import pathlib
from typing import Optional, Union

import SimpleITK as sitk
from pydicom import dcmread

from imgtools.dicom.dicom_metadata_old import get_modality_metadata
from imgtools.modalities import PET, Dose, Scan, Segmentation, StructureSet


def read_image(path: str) -> sitk.Image:
    """Read an image from the specified file path using SimpleITK.

    Parameters
    ----------
    path : str
        The file path to the image.

    Returns
    -------
    sitk.Image
        The image read from the file.
    """
    return sitk.ReadImage(path)


def read_dicom_series(
    path: str,
    series_id: list[str] | None = None,
    recursive: bool = False,
    file_names: list[str] | None = None,
) -> sitk.Image:
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
    The loaded image.
    """
    reader = sitk.ImageSeriesReader()
    if file_names is None:
        # extract the names of the dicom files that are in the path variable, which is a directory
        file_names = reader.GetGDCMSeriesFileNames(
            path,
            seriesID=series_id if series_id else "",
            recursive=recursive,
        )

    reader.SetFileNames(file_names)

    # Configure the reader to load all of the DICOM tags (public+private):
    # By default tags are not loaded (saves time).
    # By default if tags are loaded, the private tags are not loaded.
    # We explicitly configure the reader to load tags, including the
    # private ones.
    reader.MetaDataDictionaryArrayUpdateOn()
    reader.LoadPrivateTagsOn()

    return reader.Execute()


def read_dicom_scan(
    path: str,
    series_id: list[str] | None = None,
    recursive: bool = False,
    file_names: list[str] | None = None,
) -> Scan:
    image = read_dicom_series(
        path,
        series_id=series_id,
        recursive=recursive,
        file_names=file_names,
    )
    return Scan(image, {})


def read_dicom_rtstruct(
    path: str,
    suppress_warnings: bool = False,
    roi_name_pattern: str | None = None,
) -> StructureSet:
    return StructureSet.from_dicom(
        path,
        suppress_warnings=suppress_warnings,
        roi_name_pattern=roi_name_pattern,
    )


def read_dicom_rtdose(path: str) -> Dose:
    return Dose.from_dicom(path=path)


def read_dicom_pet(path: str, series: Optional[str] = None) -> PET:
    return PET.from_dicom(path=path, series_id=series, pet_image_type="SUV")


def read_dicom_seg(
    path: str, meta: dict, series: Optional[str] = None
) -> Segmentation:
    seg_img = read_dicom_series(path, series)
    return Segmentation.from_dicom(seg_img, meta)


auto_dicom_result = Union[Scan, PET, StructureSet, Dose, Segmentation]


def read_dicom_auto(
    path: str, series=None, file_names=None
) -> auto_dicom_result:
    dcms = (
        list(pathlib.Path(path).rglob("*.dcm"))
        if not path.endswith(".dcm")
        else [pathlib.Path(path)]
    )

    for dcm_path in dcms:
        dcm = dcm_path.as_posix()
        meta = dcmread(dcm, stop_before_pixels=True)
        if meta.SeriesInstanceUID != series and series is not None:
            continue

        modality = meta.Modality

        match modality:
            case "CT" | "MR":
                obj = read_dicom_scan(path, series, file_names=file_names)
            case "PT":
                obj = read_dicom_pet(path, series)
            case "RTSTRUCT":
                obj = read_dicom_rtstruct(dcm)
            case "RTDOSE":
                obj = read_dicom_rtdose(dcm)
            case "SEG":
                obj = read_dicom_seg(path, meta, series)
            case _:
                errmsg = (
                    f"Modality {modality} not supported in read_dicom_auto."
                )
                raise NotImplementedError(errmsg)

        obj.metadata.update(get_modality_metadata(meta, modality))
        return obj
