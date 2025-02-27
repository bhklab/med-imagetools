from imgtools.dicom.input.dicom_reader import DicomInput, load_dicom

__all__ = ["rtplan_reference_uids", "RTPLANReferenceSOPInstanceUIDs"]


class RTPLANReferenceSOPInstanceUIDs(list):
    """
    Represents a list of SOPInstanceUIDs pertaining to a RTSTRUCT
    referenced in an RTPLAN file
    """

    pass

def rtplan_reference_uids(
    rtplan: DicomInput,
) -> RTPLANReferenceSOPInstanceUIDs | None:
    """Get the ReferencedSOPInstanceUIDs from an RTPLAN file

    We assume RTPLAN only references a `RTSTRUCT` file.

    Example
    -------
    >>> p = "/path/to/rtplan.dcm"
    >>> match rtplan_reference_uids(p):
    ...     case RTPLANReferenceSOPInstanceUIDs(uids):
    ...         print(f"SOPInstanceUIDs: {uids=}")
    ...     case None:
    ...         print("No Reference UIDs found")
    """
    plan = load_dicom(rtplan)
    if "ReferencedStructureSetSequence" in plan:
        return RTPLANReferenceSOPInstanceUIDs(
            [
                seq.ReferencedSOPInstanceUID
                for seq in plan.ReferencedStructureSetSequence
            ]
        )
    return None




if __name__ == "__main__":
    from rich import print  # type: ignore

    ps = [
        "testdata/HN-HGJ-072/RTPLAN_Series-58071/1-1.dcm",
        "testdata/VS-SEG-002/RTPLAN_Series-22208/00000001.dcm",
        "testdata/VS-SEG-002/RTPLAN_Series-04388/00000001.dcm",
        "testdata/VS-SEG-001/RTPLAN_Series-69252/00000001.dcm",
        "testdata/VS-SEG-001/RTPLAN_Series-25725/00000001.dcm",
        "testdata/HN-CHUS-082/RTPLAN_Series-37374/1-1.dcm",
        "testdata/HN-CHUS-052/RTPLAN_Series-04314/1-1.dcm",
    ]
    for p in ps:
        match rtplan_reference_uids(p):
            case RTPLANReferenceSOPInstanceUIDs(uids):
                print(f"For {p=}:\n{len(uids)=}\n{uids=}\n\n")
            case None:
                print("No Reference UIDs found")
