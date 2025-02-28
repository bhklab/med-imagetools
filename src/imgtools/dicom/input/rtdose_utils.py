from imgtools.dicom.input.dicom_reader import DicomInput, load_dicom

__all__ = ["rtdose_reference_uids", "RTDOSERefStructSOP", "RTDOSERefPlanSOP"]

from imgtools.logging import logger

# class representing a ReferencedRTStructureSetSequence


class RTDOSERefStructSOP(str):
    """
    Represents a SOPInstanceUID to a RTSTRUCT file in a RTDOSE file
    """

    pass


class RTDOSERefPlanSOP(str):
    """
    Represents a SOPInstanceUID to a RTPLAN file in a RTDOSE file
    """

    pass


def rtdose_reference_uids(
    rtdose: DicomInput,
) -> RTDOSERefStructSOP | RTDOSERefPlanSOP | None:
    """Get the ReferencedSOPInstanceUIDs from an RTDOSE file

    Notes
    -----
    We prioritize the ReferencedStructureSetSequence over the
    ReferencedRTPlanSequence. If both are present, we return the
    ReferencedStructureSetSequence SOPInstanceUID.
    If the ReferencedStructureSetSequence is not present, we return
    the ReferencedRTPlanSequence SOPInstanceUID and hope that the
    RTPLAN references the RTSTRUCT.

    Example
    -------
    >>> d = "/path/to/rtdose.dcm"
    >>> match rtdose_reference_uids(d):
    ...     case RTDOSERefStructSOP(uid):
    ...         print(f"RTSTRUCT UID: {uid}")
    ...     case RTDOSERefPlanSOP(uid):
    ...         print(f"RTPLAN UID: {uid}")
    ...     case None:
    ...         print(
    ...             "No ReferencedSOPInstanceUID found"
    ...         )
    """
    dose = load_dicom(rtdose)
    if "ReferencedStructureSetSequence" in dose:
        ref_struct = [
            seq.ReferencedSOPInstanceUID
            for seq in dose.ReferencedStructureSetSequence
        ]
        if len(ref_struct) > 1:
            warnmsg = (
                f"Found {len(ref_struct)}"
                " ReferencedStructureSetSequence in RTDOSE file"
                "Using the first one"
            )
            logger.warning(warnmsg, file=rtdose)
        return RTDOSERefStructSOP(ref_struct[0])
    elif "ReferencedRTPlanSequence" in dose:
        ref_pl = [
            seq.ReferencedSOPInstanceUID
            for seq in dose.ReferencedRTPlanSequence
        ]
        if len(ref_pl) > 1:
            warnmsg = (
                f"Found {len(ref_pl)} ReferencedRTPlanSequence in RTDOSE file"
                "Using the first one"
            )
            logger.warning(warnmsg, file=rtdose)
        return RTDOSERefPlanSOP(ref_pl[0])

    return None
