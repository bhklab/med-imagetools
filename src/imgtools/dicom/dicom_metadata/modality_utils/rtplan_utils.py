from pydicom.dataset import Dataset

from imgtools.loggers import logger

__all__ = ["rtplan_reference_uids", "RTPLANRefStructSOP"]


class RTPLANRefStructSOP(str):
    """
    Represents a `SOPInstanceUID` pointing to a `RTSTRUCT`
    referenced by a `RTPLAN` file

    extracted via `ReferencedStructureSetSequence.ReferencedSOPInstanceUID`
    """

    pass


def rtplan_reference_uids(
    rtplan: Dataset,
) -> RTPLANRefStructSOP:
    """Get the ReferencedSOPInstanceUIDs from an RTPLAN file

    We assume RTPLAN only references a `RTSTRUCT` file.

    Parameters
    ----------
    rtplan : Dataset
        The RTPLAN file to extract the reference UIDs from
        Must be a `pydicom.Dataset` object

    Example
    -------
    >>> match rtplan_reference_uids(rtplan):
    ...     case RTPLANRefStructSOP(uid):
    ...         print(f"SOPInstanceUID: {uid=}")
    """
    if "ReferencedStructureSetSequence" in rtplan:
        refs = [
            RTPLANRefStructSOP(seq.ReferencedSOPInstanceUID)
            for seq in rtplan.ReferencedStructureSetSequence
        ]
        if len(refs) > 1:
            warnmsg = (
                f"Found {len(refs)} RTSTRUCT references in {rtplan=}. "
                "Only the first one will be used."
            )
            logger.warning(warnmsg)
        return refs[0]

    return RTPLANRefStructSOP("")
