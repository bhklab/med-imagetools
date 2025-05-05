from pydicom.dataset import Dataset

__all__ = [
    "rtdose_reference_uids",
    "RTDOSERefStructSOP",
    "RTDOSERefPlanSOP",
    "RTDOSERefSeries",
]


class RTDOSERefSeries(str):
    """
    Sometimes... they reference the SERIESUID as well (Head-Neck-Pet-CT...)
    but they also call it the SOPInstanceUID for some reason lol

    `dose.ReferencedImageSequence[0].ReferencedSOPInstanceUID`
    """


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
    rtdose: Dataset,
) -> tuple[RTDOSERefPlanSOP, RTDOSERefStructSOP, RTDOSERefSeries]:
    """Extracts referenced SOPInstanceUIDs from an RTDOSE file.

    Parameters
    ----------
    rtdose : Dataset
        DICOM RTDOSE dataset as a pydicom Dataset.

    Returns
    -------
    tuple[RTDOSERefPlanSOP, RTDOSERefStructSOP, RTDOSERefSeries]
        A tuple containing:
        - plan_uid: RTDOSERefPlanSOP - Referenced RTPLAN SOPInstanceUID (empty string if not found)
        - struct_uid: RTDOSERefStructSOP - Referenced RTSTRUCT SOPInstanceUID (empty string if not found)
        - series_uid: RTDOSERefSeries - Referenced Series SOPInstanceUID (empty string if not found)
    """

    # Extract plan UID
    plan_uid = RTDOSERefPlanSOP("")
    if (
        "ReferencedRTPlanSequence" in rtdose
        and rtdose.ReferencedRTPlanSequence
    ):
        plan_uid = RTDOSERefPlanSOP(rtdose.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID)  # fmt: skip

    # Extract structure set UID
    struct_uid = RTDOSERefStructSOP("")
    if ("ReferencedStructureSetSequence" in rtdose and rtdose.ReferencedStructureSetSequence):  # fmt: skip
        struct_uid = RTDOSERefStructSOP(rtdose.ReferencedStructureSetSequence[0].ReferencedSOPInstanceUID)  # fmt: skip

    # Extract series UID
    series_uid = RTDOSERefSeries("")
    if "ReferencedImageSequence" in rtdose and rtdose.ReferencedImageSequence:
        series_uid = RTDOSERefSeries(rtdose.ReferencedImageSequence[0].ReferencedSOPInstanceUID)  # fmt: skip

    return plan_uid, struct_uid, series_uid


# from rich import print

# p = "data/OCTANE_DATA/OCTANE_ALL/HN-HGJ-072/StudyUID-16252/RTDOSE/6780042-SeriesUID-98557/1-1.dcm"

# refd_plan, refd_struct, refd_series = rtdose_reference_uids(p)

#     case [refd_plan, refd_struct, refd_series]:
#         print(f"RTPLAN UID: {refd_plan}, RTSTRUCT UID: {refd_struct}, Series UID: {refd_series}")

# print(f"RTSTRUCT UID: {s}, RTPLAN UID: {p}, Series UID: {sr}")
# case [RTDOSERefPlanSOP(p), None, RTDOSERefSeries(sr)]:
#     print(f"RTPLAN UID: {p}, Series UID: {sr}")
# case RTDOSERefs(struct=uid, plan=None, series=None):
#     print(f"Only RTSTRUCT UID found: {uid}")
# case RTDOSERefs(struct=None, plan=RTDOSERefPlanSOP(uid), series=None):
#     print(f"Only RTPLAN UID found: {uid}")
# case RTDOSERefs(struct=None, plan=None, series=RTDOSERefSeries(uid)):
#     print(f"Only Series UID found: {uid}")
# case RTDOSERefs(
#     struct=s,
#     plan=p,
#     series=sr,
# ):
#     print(f"RTSTRUCT UID: {s}, RTPLAN UID: {p}, Series UID: {sr}")
# case RTDOSERefs():
#     print("No referenced UIDs found")
