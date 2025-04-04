from pydicom.dataset import Dataset

from imgtools.exceptions import (
    RTSTRUCTAttributeError,
)

__all__ = [
    "extract_roi_meta",
    "extract_roi_names",
    "rtstruct_reference_uids",
    "RTSTRUCTRefSeries",
    "RTSTRUCTRefSOP",
]


def extract_roi_meta(rtstruct: Dataset) -> list[dict[str, str]]:
    """Extract ROI metadata from an RTSTRUCT DICOM file.

    Iterate over the `StructureSetROISequence` in the RTSTRUCT file and extract:
        - "ROINumber": Unique identifier for the ROI.
        - "ROIName": Name of the ROI.
        - "ROIGenerationAlgorithm": Algorithm used to generate the ROI.

    Parameters
    ----------
    rtstruct : `pydicom.dataset.Dataset`

    Returns
    -------
    list of dict[str, str]
        A list of dictionaries, each containing metadata for an ROI.

    Raises
    ------
    RTSTRUCTAttributeError
        If the RTSTRUCT file does not contain the required `StructureSetROISequence`.
    """

    try:
        roi_sequence = rtstruct.StructureSetROISequence
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


def extract_roi_names(rtstruct: Dataset) -> list[str]:
    """Extract a list of ROI names from an RTSTRUCT DICOM file.

    Parameters
    ----------
    rtstruct : `pydicom.dataset.Dataset`

    Returns
    -------
    list of str
        A list of ROI names extracted from the RTSTRUCT file.

    Raises
    ------
    RTSTRUCTAttributeError
        If the RTSTRUCT file does not contain the required `StructureSetROISequence`.
    """

    roi_metas = extract_roi_meta(rtstruct)
    roi_names = [roi_meta["ROIName"] for roi_meta in roi_metas]
    return roi_names


class RTSTRUCTRefSeries(str):
    """
    A string subclass representing the SeriesInstanceUID referenced by an RTSTRUCT file.

    Used for type annotations and to distinguish this particular reference type.
    """

    pass


class RTSTRUCTRefSOP(list[str]):
    """
    A list subclass representing the SOPInstanceUIDs referenced by an RTSTRUCT file.

    Contains the UIDs of individual DICOM instances that the structure set references.
    """

    pass


def rtstruct_reference_uids(
    rtstruct: Dataset,
) -> tuple[RTSTRUCTRefSeries, RTSTRUCTRefSOP]:
    """Retrieve the referenced SeriesInstanceUID and SOP UIDs from an RTSTRUCT.

    Parameters
    ----------
    rtstruct : Dataset
        DICOM RTSTRUCT dataset as a pydicom Dataset.

    Returns
    -------
    tuple[RTSTRUCTRefSeries, RTSTRUCTRefSOP]
        - Referenced SeriesInstanceUID as RTSTRUCTRefSeries (empty string if unavailable)
        - Referenced SOPInstanceUIDs as RTSTRUCTRefSOP (empty list if unavailable)
    """
    import contextlib

    series_uid = ""
    sop_uids: list[str] = []

    with contextlib.suppress(AttributeError, IndexError):
        # Direct access attempt - if any part fails, we'll catch the exception
        ref_sequence = rtstruct.ReferencedFrameOfReferenceSequence[0]
        rt_ref_series = ref_sequence.RTReferencedStudySequence[
            0
        ].RTReferencedSeriesSequence[0]

        # Extract series UID if available
        series_uid = rt_ref_series.get("SeriesInstanceUID", "")

        cis = rt_ref_series.ContourImageSequence[0]
        sop_uids.extend(
            [
                ci.ReferencedSOPInstanceUID
                for ci in cis
                if "ReferencedSOPInstanceUID" in ci
            ]
        )

    return RTSTRUCTRefSeries(series_uid), RTSTRUCTRefSOP(sop_uids)
