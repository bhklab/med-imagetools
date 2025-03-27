from imgtools.dicom.dicom_reader import DicomInput, load_dicom
from imgtools.logging import logger

__all__ = ["rtplan_reference_uids", "RTPLANRefStructSOP"]


class RTPLANRefStructSOP(str):
    """
    Represents a `SOPInstanceUID` pointing to a `RTSTRUCT`
    referenced by a `RTPLAN` file

    extracted via `ReferencedStructureSetSequence.ReferencedSOPInstanceUID`
    """

    pass


def rtplan_reference_uids(
    rtplan: DicomInput,
) -> RTPLANRefStructSOP | None:
    """Get the ReferencedSOPInstanceUIDs from an RTPLAN file

    We assume RTPLAN only references a `RTSTRUCT` file.

    Example
    -------
    >>> p = "/path/to/rtplan.dcm"
    >>> match rtplan_reference_uids(p):
    ...     case RTPLANRefStructSOP(uid):
    ...         print(f"SOPInstanceUID: {uid=}")
    ...     case None:
    ...         print("No Reference UIDs found")
    """
    plan = load_dicom(rtplan)
    if "ReferencedStructureSetSequence" in plan:
        refs = [
            RTPLANRefStructSOP(seq.ReferencedSOPInstanceUID)
            for seq in plan.ReferencedStructureSetSequence
        ]
        if len(refs) > 1:
            warnmsg = (
                f"Found {len(refs)} RTSTRUCT references in {rtplan=}. "
                "Only the first one will be used."
            )
            logger.warning(warnmsg)
        return refs[0]

    return None
