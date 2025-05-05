from pydicom.dataset import Dataset

"""
StructuredReport (SR)

Note on References:
-------------------
From my initial glance, it looks like SR files can reference MORE than ONE SeriesInstanceUID

Looks like within a 'ReferencedSeriesSequence' there can be multiple unique SeriesInstanceUIDs
so two layers of iteration is needed to get all the SeriesInstanceUIDs

CurrentRequestedProcedureEvidenceSequence = [
    ReferencedSeriesSequence = [
          {
            SeriesInstanceUID = str,
            ReferencedSOPSequence = [
                ReferencedSOPInstanceUID = str
          },
          {
            SeriesInstanceUID = str, # this can be different from the above
            ReferencedSOPSequence = [
                ReferencedSOPInstanceUID = str
          }
        ]
    ],
    ReferencedSeriesSequence = [
    ....
]
so what we want to do is iterate through each 

for ReferencedSeriesSequence in CurrentRequestedProcedureEvidenceSequence:
    for item in ReferencedSeriesSequence:
        get the SeriesInstanceUID
"""


__all__ = [
    "sr_reference_uids",
    "SR_RefSeries",
    "SR_RefSOPs",
]


class SR_RefSeries(list):  # noqa
    """
    Represents a list of `SeriesInstanceUID`s referenced by a `SR` file
    """

    pass


class SR_RefSOPs(list):  # noqa
    """
    Represents a list of unique `SOPInstanceUID`s referenced in by a `SR` file
    """

    pass


def sr_reference_uids(
    sr: Dataset,
) -> tuple[SR_RefSeries, SR_RefSOPs]:
    """Get the `ReferencedSeriesInstanceUID`s from an SR file

    SR Dicom files can reference multiple SeriesInstanceUIDs and many SOPInstanceUIDs

    Since we might need to match on SOP Instance UIDs if the reference is
    a MR, we also get the SOP Instance UIDs
    This function extracts all unique references from the
    CurrentRequestedProcedureEvidenceSequence.

    Parameters
    ----------
    sr : Dataset
        DICOM Structured Report dataset as a pydicom Dataset.

    Returns
    -------
    tuple[SR_RefSeries, SR_RefSOPs]
        A tuple containing:
        - series_uids: SR_RefSeries - List of unique referenced SeriesInstanceUIDs (empty list if none)
        - sop_uids: SR_RefSOPs - List of unique referenced SOPInstanceUIDs (empty list if none)
    """

    series_uids = set()
    sop_uids = set()
    if "CurrentRequestedProcedureEvidenceSequence" not in sr:
        return SR_RefSeries([]), SR_RefSOPs([])

    for evidence_seq in sr.CurrentRequestedProcedureEvidenceSequence:
        if "ReferencedSeriesSequence" not in evidence_seq:
            continue

        for series_seq in evidence_seq.ReferencedSeriesSequence:
            series_uids.add(series_seq.SeriesInstanceUID)

            if "ReferencedSOPSequence" not in series_seq:
                continue
            for ref_seq in series_seq.ReferencedSOPSequence:
                sop_uids.add(ref_seq.ReferencedSOPInstanceUID)

    series_list = SR_RefSeries(series_uids)
    sop_list = SR_RefSOPs(sop_uids)

    return series_list, sop_list
