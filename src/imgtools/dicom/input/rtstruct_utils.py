from typing import TYPE_CHECKING

from imgtools.exceptions import (
    RTSTRUCTAttributeError,
)

from .dicom_reader import (
    DicomInput,
    load_rtstruct_dcm,
)

if TYPE_CHECKING:
    from pydicom.dataset import FileDataset


def extract_roi_meta(rtstruct: DicomInput) -> list[dict[str, str]]:
    """Extract ROI metadata from an RTSTRUCT DICOM file.

    Iterate over the `StructureSetROISequence` in the RTSTRUCT file and extract:
        - "ROINumber": Unique identifier for the ROI.
        - "ROIName": Name of the ROI.
        - "ROIGenerationAlgorithm": Algorithm used to generate the ROI.

    Parameters
    ----------
    rtstruct : FileDataset | str | Path | bytes
        Input RTSTRUCT DICOM dataset or file path.

    Returns
    -------
    list of dict[str, str]
        A list of dictionaries, each containing metadata for an ROI.

    Raises
    ------
    RTSTRUCTAttributeError
        If the RTSTRUCT file does not contain the required `StructureSetROISequence`.
    """

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
    """Extract a list of ROI names from an RTSTRUCT DICOM file.

    Parameters
    ----------
    rtstruct : FileDataset | str | Path | bytes
        Input RTSTRUCT DICOM dataset or file path.

    Returns
    -------
    list of str
        A list of ROI names extracted from the RTSTRUCT file.

    Raises
    ------
    RTSTRUCTAttributeError
        If the RTSTRUCT file does not contain the required `StructureSetROISequence`.
    """
    dcm_rtstruct: FileDataset = load_rtstruct_dcm(rtstruct)
    try:
        roi_sequence = dcm_rtstruct.StructureSetROISequence
    except AttributeError as e:
        errmsg = "Failed to extract ROISequence from the RTSTRUCT file."
        raise RTSTRUCTAttributeError(errmsg) from e
    roi_names = [roi.ROIName for roi in roi_sequence]
    return roi_names


def rtstruct_reference_uids(rtstruct: DicomInput) -> tuple[str, str]:
    """Retrieve the referenced SeriesInstanceUID and StudyInstanceUID from an RTSTRUCT.

    Parameters
    ----------
    rtstruct : FileDataset | str | Path | bytes
        Input RTSTRUCT DICOM dataset or file path.

    Returns
    -------
    tuple[str, str]
        - Referenced `SeriesInstanceUID` (str).
        - Referenced `StudyInstanceUID` (str).

    Raises
    ------
    RTSTRUCTAttributeError
        If the RTSTRUCT file does not contain the required reference fields.
    """
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
