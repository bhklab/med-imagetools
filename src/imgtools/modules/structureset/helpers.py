from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Sequence, TypedDict, Union

from pydicom import dcmread
from pydicom.dataset import FileDataset

from imgtools.modules.structureset.custom_types import RTSTRUCTMetadata


def load_rtstruct_data(rtstruct_input: str | Path | bytes) -> FileDataset:
    """Load an RTSTRUCT DICOM file or bytes data and return the FileDataset object.

    Parameters
    ----------
    rtstruct_input : str | Path | bytes
        Path to the RTSTRUCT file or its content as bytes.

    Returns
    -------
    FileDataset
        Parsed RTSTRUCT DICOM object.

    Raises
    ------
    ValueError
        If the input type is unsupported or the file is not an RTSTRUCT.
    """
    match rtstruct_input:
        case str() | Path():
            dicom = dcmread(rtstruct_input, force=True)
        case bytes():
            dicom = dcmread(BytesIO(rtstruct_input), force=True)
        case _:
            raise ValueError(
                f"Invalid input type for 'rtstruct_input': {type(rtstruct_input)}. "
                "Must be a str, Path, or bytes object."
            )

    if dicom.Modality != "RTSTRUCT":
        errmsg = f"The provided DICOM is not an RTSTRUCT file. Found Modality: {dicom.Modality}"
        raise ValueError(errmsg)

    return dicom


def extract_roi_names(rtstruct: FileDataset | str | Path | bytes) -> list[str]:
    """Extract ROI names from an RTSTRUCT file or dataset.

    Parameters
    ----------
    rtstruct : FileDataset | str | Path | bytes
        An RTSTRUCT FileDataset object, or a path/bytes to load it.

    Returns
    -------
    list[str]
        List of ROI names extracted from the RTSTRUCT.

    Raises
    ------
    ValueError
        If the ROI names cannot be extracted.
    """
    match rtstruct:
        case FileDataset():
            loaded_rtstruct = rtstruct
        case str() | Path() | bytes():
            loaded_rtstruct = load_rtstruct_data(rtstruct)
        case _:
            errmsg = "Invalid input type for 'rtstruct'. Must be FileDataset, str, Path, or bytes."
            raise ValueError(errmsg)

    try:
        return [roi.ROIName for roi in loaded_rtstruct.StructureSetROISequence]
    except (AttributeError, IndexError) as e:
        errmsg = "Failed to extract ROI names from the RTSTRUCT file."
        raise ValueError(errmsg) from e


def rtstruct_reference_seriesuid(
    rtstruct_or_path: Union[str, Path, FileDataset],
) -> str:
    """Given an RTSTRUCT file or loaded RTSTRUCT, return the Referenced SeriesInstanceUID."""
    rtstruct = (
        load_rtstruct_data(rtstruct_or_path)
        if isinstance(rtstruct_or_path, (str, Path, bytes))
        else rtstruct_or_path
    )
    try:
        return str(
            rtstruct.ReferencedFrameOfReferenceSequence[0]
            .RTReferencedStudySequence[0]
            .RTReferencedSeriesSequence[0]
            .SeriesInstanceUID
        )
    except (AttributeError, IndexError) as e:
        raise ValueError("Referenced SeriesInstanceUID not found in RTSTRUCT") from e


def extract_rtstruct_metadata(rtstruct: FileDataset | str | Path | bytes) -> RTSTRUCTMetadata:
    """Extract metadata from the RTSTRUCT file."""
    match rtstruct:
        case FileDataset():
            loaded_rtstruct = rtstruct
        case str() | Path() | bytes():
            loaded_rtstruct = load_rtstruct_data(rtstruct)
        case _:
            errmsg = "Invalid input type for 'rtstruct'. Must be FileDataset, str, Path, or bytes."
            raise ValueError(errmsg)

    return RTSTRUCTMetadata(
        PatientID=loaded_rtstruct.PatientID,
        StudyInstanceUID=loaded_rtstruct.StudyInstanceUID,
        SeriesInstanceUID=loaded_rtstruct.SeriesInstanceUID,
        Modality=loaded_rtstruct.Modality,
        ReferencedSeriesInstanceUID=rtstruct_reference_seriesuid(loaded_rtstruct),
        OriginalROINames=(roi_names := extract_roi_names(loaded_rtstruct)),
        OriginalNumberOfROIs=len(roi_names),
    )
