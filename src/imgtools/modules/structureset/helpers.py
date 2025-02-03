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
from imgtools.modules.structureset.custom_types import (
    ROIMetadata,
    RTSTRUCTMetadata,
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
    rtstruct_input : str | Path | bytes
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


# Example usage of the decorator with refactored functions
def extract_roi_meta(rtstruct: DicomInput) -> list[dict[str, str]]:
    """Extract ROI names from a FileDataset."""
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


def rtstruct_reference_seriesuid(rtstruct: DicomInput) -> tuple[str, str]:
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


def extract_rtstruct_metadata(rtstruct: DicomInput) -> RTSTRUCTMetadata:
    """Extract metadata from the RTSTRUCT file."""
    dcm_rtstruct: FileDataset = load_rtstruct_dcm(rtstruct)
    roi_metas: list[dict[str, str]] = extract_roi_meta(dcm_rtstruct)
    rt_ref_series, rt_ref_study = rtstruct_reference_seriesuid(dcm_rtstruct)
    return RTSTRUCTMetadata(
        PatientID=dcm_rtstruct.PatientID,
        StudyInstanceUID=dcm_rtstruct.StudyInstanceUID,
        SeriesInstanceUID=dcm_rtstruct.SeriesInstanceUID,
        Modality=dcm_rtstruct.Modality,
        ReferencedStudyInstanceUID=rt_ref_study,
        ReferencedSeriesInstanceUID=rt_ref_series,
        OriginalROIMeta=[ROIMetadata(**roi_meta) for roi_meta in roi_metas],
        OriginalNumberOfROIs=len(roi_metas),
    )


if __name__ == "__main__":  # pragma: no cover
    import timeit

    from rich import print  # noqa
    # Load an RTSTRUCT file and extract metadata

    # Benchmark the metadata extraction 100 times
    rtstruct_path = Path(
        "/home/bioinf/bhklab/radiomics/readii-negative-controls/rawdata/RADCURE/images/dicoms/RADCURE-0006/StudyUID-46105/RTSTRUCT_SeriesUID-32605/00000001.dcm"
    )

    def benchmark() -> None:
        extract_rtstruct_metadata(rtstruct_path)

    # config
    REPEAT = 5
    NUMBER = 10

    print(f"Benchmark times for {REPEAT} repeats of {NUMBER} iterations:")  # noqa

    times = timeit.repeat(benchmark, repeat=REPEAT, number=NUMBER)
    print(  # noqa
        f"Average time per {NUMBER} iterations: {sum(times) / len(times):.6f} seconds"
    )

    result = extract_rtstruct_metadata(rtstruct_path)

    print(result)  # noqa
