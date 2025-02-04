from io import BytesIO
from pathlib import Path
from typing import TypeAlias

from pydicom import dcmread
from pydicom.dataset import FileDataset

from imgtools.exceptions import (
    InvalidDicomError,
    NotRTSTRUCTError,
    RTSTRUCTAttributeError,
)

# Define a type alias for DICOM input types
DicomInput: TypeAlias = FileDataset | str | Path | bytes


def load_rtstruct_dcm(
    rtstruct_input: DicomInput,
    force: bool = True,
    stop_before_pixels: bool = True,
) -> FileDataset:
    """Load an RTSTRUCT DICOM file or bytes data and return the FileDataset object.

    Parameters
    ----------
    rtstruct_input : pydicom.FileDataset | str | Path | bytes
        Path to the RTSTRUCT file or its content as bytes.
    force: bool (default = True)
        ignore dicoms that are missing their *File Meta Information* header.
    stop_before_pixels : bool
        If True, stop reading the DICOM file before the pixel data, by default True

    Returns
    -------
    FileDataset
        Parsed RTSTRUCT DICOM object.

    Raises
    ------
    InvalidDicomError
        If the input type is unsupported or the file is not an RTSTRUCT.
    NotRTSTRUCTError
        if the Modality field in the dicom is not `RTSTRUCT`
    """
    match rtstruct_input:
        case FileDataset():
            dicom = rtstruct_input
        case str() | Path():
            dicom = dcmread(
                rtstruct_input,
                force=force,
                stop_before_pixels=stop_before_pixels,
            )
        case bytes():
            dicom = dcmread(
                BytesIO(rtstruct_input),
                force=force,
                stop_before_pixels=stop_before_pixels,
            )
        case _:
            msg = (
                f"Invalid input type for 'rtstruct_input': {type(rtstruct_input)}. "
                "Must be a str, Path, or bytes object."
            )
            raise InvalidDicomError(msg)

    if dicom.Modality != "RTSTRUCT":
        msg = f"The provided DICOM is not an RTSTRUCT file. Found Modality: {dicom.Modality}"
        raise NotRTSTRUCTError(msg)

    return dicom


def extract_roi_meta(rtstruct: DicomInput) -> list[dict[str, str]]:
    """Extract ROI metadata from an RTSTRUCT FileDataset."""
    dcm_rtstruct: FileDataset = load_rtstruct_dcm(rtstruct)
    try:
        roi_sequence = dcm_rtstruct.StructureSetROISequence
    except AttributeError as e:
        errmsg = "Failed to extract ROISequence from the RTSTRUCT file."
        raise RTSTRUCTAttributeError(errmsg) from e
    roi_metas = []
    for roi in roi_sequence:
        roi_meta = {}
        roi_meta["ROINumber"] = getattr(roi, "ROINumber", "")
        roi_meta["ROIName"] = getattr(roi, "ROIName", "")
        roi_meta["ROIGenerationAlgorithm"] = getattr(
            roi, "ROIGenerationAlgorithm", ""
        )
        roi_metas.append(roi_meta)
    return roi_metas


def extract_roi_names(rtstruct: DicomInput) -> list[str]:
    """Extract ROI names from a FileDataset."""
    dcm_rtstruct: FileDataset = load_rtstruct_dcm(rtstruct)
    try:
        roi_sequence = dcm_rtstruct.StructureSetROISequence
    except AttributeError as e:
        errmsg = "Failed to extract ROISequence from the RTSTRUCT file."
        raise RTSTRUCTAttributeError(errmsg) from e
    roi_names = [roi.ROIName for roi in roi_sequence]
    return roi_names


def rtstruct_reference_uids(rtstruct: DicomInput) -> tuple[str, str]:
    """Return the Referenced SeriesInstanceUID and Referenced StudyInstanceUID from an RTSTRUCT."""
    dcm_rtstruct: FileDataset = load_rtstruct_dcm(rtstruct)
    try:
        referenced_series_instance_uid = str(
            dcm_rtstruct.ReferencedFrameOfReferenceSequence[0]
            .RTReferencedStudySequence[0]
            .RTReferencedSeriesSequence[0]
            .SeriesInstanceUID
        )
        referenced_study_instance_uid = str(
            dcm_rtstruct.ReferencedFrameOfReferenceSequence[0]
            .RTReferencedStudySequence[0]
            .ReferencedSOPInstanceUID
        )
        return referenced_series_instance_uid, referenced_study_instance_uid
    except (AttributeError, IndexError) as e:
        errmsg = "Failed to extract Referenced SeriesInstanceUID or Referenced StudyInstanceUID from the RTSTRUCT file."
        raise RTSTRUCTAttributeError(errmsg) from e
