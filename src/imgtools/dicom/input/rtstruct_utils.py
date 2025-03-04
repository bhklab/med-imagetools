from typing import TYPE_CHECKING

from imgtools.dicom.input.dicom_reader import (
    DicomInput,
    load_rtstruct_dcm,
)
from imgtools.exceptions import (
    RTSTRUCTAttributeError,
)

if TYPE_CHECKING:
    from pydicom.dataset import FileDataset

__all__ = [
    "extract_roi_meta",
    "extract_roi_names",
    "rtstruct_reference_uids",
    "RTSTRUCTRefSeries",
    "RTSTRUCTRefStudy",
    "RTSTRUCTRefSOP",
]


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


class RTSTRUCTRefSeries(str):
    """Referenced SeriesInstanceUID from an RTSTRUCT file."""

    pass


class RTSTRUCTRefStudy(str):
    """Referenced StudyInstanceUID from an RTSTRUCT file."""

    pass


class RTSTRUCTRefSOP(str):
    """One (1) Referenced SOPInstanceUID from an RTSTRUCT file."""

    pass


def rtstruct_reference_uids(
    rtstruct: DicomInput,
) -> tuple[RTSTRUCTRefSeries, RTSTRUCTRefStudy] | RTSTRUCTRefSOP:
    """Retrieve the referenced SeriesInstanceUID and StudyInstanceUID from an RTSTRUCT.

    Parameters
    ----------
    rtstruct : FileDataset | str | Path | bytes
        Input RTSTRUCT DICOM dataset or file path.

    Returns
    -------
    tuple[RTSTRUCTRefSeries, RTSTRUCTRefStudy] | RTSTRUCTRefSOP
        If the RTSTRUCT file contains the required reference fields:
            - Referenced `SeriesInstanceUID` (RTSTRUCTRefSeries)
            - Referenced `StudyInstanceUID` (RTSTRUCTRefStudy)
        If the RTSTRUCT file does not contain the required reference fields:
            - Referenced `SOPInstanceUID` (RTSTRUCTRefSOP)

    Raises
    ------
    RTSTRUCTAttributeError
        If the RTSTRUCT file does not contain the required reference fields.

    Notes
    -----
    Opinionated compared to other reference extractions in that we expect the RTSTRUCT file
    to contain ATLEAST the RefSeries OR a RefSOP. If neither are found, an error is raised.
    """
    dcm_rtstruct: FileDataset = load_rtstruct_dcm(rtstruct)
    try:
        referenced_series_instance_uid = RTSTRUCTRefSeries(
            dcm_rtstruct.ReferencedFrameOfReferenceSequence[0]
            .RTReferencedStudySequence[0]
            .RTReferencedSeriesSequence[0]
            .SeriesInstanceUID
        )
        referenced_study_instance_uid = RTSTRUCTRefStudy(
            dcm_rtstruct.ReferencedFrameOfReferenceSequence[0]
            .RTReferencedStudySequence[0]
            .ReferencedSOPInstanceUID
        )
        return referenced_series_instance_uid, referenced_study_instance_uid
    except (AttributeError, IndexError) as e:
        errmsg = "Failed to extract Referenced SeriesInstanceUID or Referenced StudyInstanceUID from the RTSTRUCT file."
        errmsg += " Attempting to extract ReferencedSOPInstanceUID."

        try:
            ref_sequence = dcm_rtstruct.ReferencedFrameOfReferenceSequence[0]

            # ref_frame_ref = ref_sequence.FrameOfReferenceUID
            ref_sop = (
                ref_sequence.RTReferencedStudySequence[0]
                .RTReferencedSeriesSequence[0]
                .ContourImageSequence[0]
                .ReferencedSOPInstanceUID
            )

            return RTSTRUCTRefSOP(ref_sop)
        except (AttributeError, IndexError) as e2:
            errmsg += f"First error message: {e}. Second error message: {e2}"
            raise RTSTRUCTAttributeError(errmsg) from e2


if __name__ == "__main__":
    from pathlib import Path

    from tqdm import tqdm

    from imgtools.dicom.find_dicoms import find_dicoms

    rtstruct_paths = find_dicoms(
        Path(
            "~/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021"
        ).expanduser(),
        recursive=True,
        check_header=False,
        extension="dcm",
        search_input=["RTSTRUCT_Series"],
    )

    series_uid_list = []
    sop_uid_list = []
    for path in tqdm(rtstruct_paths):
        match rtstruct_reference_uids(path):
            case RTSTRUCTRefSeries(series_uid), _:
                series_uid_list.append(series_uid)
            case RTSTRUCTRefSOP(sop_uid):
                sop_uid_list.append(sop_uid)

    # print table of # of series_uids and sop_uids
    print(f"{'series_uid':<20}|{'sop_uid':<20}")
    print(f"{'-' * 20:<20}{'-' * 20:<20}")
    print(f"{len(series_uid_list):<20}|{len(sop_uid_list):<20}")
