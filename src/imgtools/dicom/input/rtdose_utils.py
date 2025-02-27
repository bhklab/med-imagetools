from imgtools.dicom.input.dicom_reader import DicomInput, load_dicom

__all__ = ["rtdose_reference_uids", "RTDOSEReferenceSOPInstanceUIDs"]


class RTDOSEReferenceSOPInstanceUIDs(list):
    """
    Represents a list of SOPInstanceUIDs pertaining to a RTSTRUCT
    referenced in an RTDOSE file
    """

    pass


def rtdose_reference_uids(
    rtdose: DicomInput,
) -> RTDOSEReferenceSOPInstanceUIDs | None:
    """Get the ReferencedSOPInstanceUIDs from an RTDOSE file

    We assume RTDOSE only references a `RTSTRUCT` file.

    Example
    -------
    >>> d = "/path/to/rtdose.dcm"
    >>> match rtdose_reference_uids(d):
    ...     case RTDOSEReferenceSOPInstanceUIDs(uids):
    ...         print(f"SOPInstanceUIDs: {uids=}")
    ...     case None:
    ...         print("No Reference UIDs found")
    """
    dose = load_dicom(rtdose)
    if "ReferencedStructureSetSequence" in dose:
        return RTDOSEReferenceSOPInstanceUIDs(
            [
                seq.ReferencedSOPInstanceUID
                for seq in dose.ReferencedStructureSetSequence
            ]
        )
    return None
