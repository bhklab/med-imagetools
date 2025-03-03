from dataclasses import dataclass

from imgtools.dicom.input.dicom_reader import DicomInput, load_dicom

__all__ = ["rtdose_reference_uids", "RTDOSERefStructSOP", "RTDOSERefPlanSOP"]

from imgtools.logging import logger


# class representing a ReferencedRTStructureSetSequence
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
    rtdose: DicomInput,
) -> list[RTDOSERefPlanSOP | RTDOSERefStructSOP | RTDOSERefSeries | None]:
    """Extracts referenced SOPInstanceUIDs from an RTDOSE file.

    Returns
    -------
    RTDOSERefs
            - struct: RTDOSERefStructSOP or None
            - plan: RTDOSERefPlanSOP or None
            - series: RTDOSERefSeries or None
    """
    dose = load_dicom(rtdose)

    result: list[
        RTDOSERefPlanSOP | RTDOSERefStructSOP | RTDOSERefSeries | None
    ] = [None for _ in range(3)]

    if "ReferencedRTPlanSequence" in dose:
        plan_uids = [
            seq.ReferencedSOPInstanceUID
            for seq in dose.ReferencedRTPlanSequence
        ]
        if plan_uids:
            result[0] = RTDOSERefPlanSOP(plan_uids[0])

        if len(plan_uids) > 1:
            logger.warning(
                f"Found {len(plan_uids)} ReferencedRTPlanSequence in"
                "RTDOSE file, using the first one",
                file=rtdose,
            )

    if "ReferencedStructureSetSequence" in dose:
        struct_uids = [
            seq.ReferencedSOPInstanceUID
            for seq in dose.ReferencedStructureSetSequence
        ]
        if struct_uids:
            result[1] = RTDOSERefStructSOP(struct_uids[0])

        if len(struct_uids) > 1:
            logger.warning(
                f"Found {len(struct_uids)} ReferencedStructureSetSequence"
                "in RTDOSE file, using the first one",
                file=rtdose,
            )

    if "ReferencedImageSequence" in dose:
        series_uids = [
            seq.ReferencedSOPInstanceUID
            for seq in dose.ReferencedImageSequence
        ]
        if series_uids:
            result[2] = RTDOSERefSeries(series_uids[0])

        if len(series_uids) > 1:
            logger.warning(
                f"Found {len(series_uids)} ReferencedRTImageSequence"
                "in RTDOSE file, using the first one",
                file=rtdose,
            )

    return result


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
