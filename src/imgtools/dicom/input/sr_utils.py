from imgtools.dicom.input.dicom_reader import DicomInput, load_dicom

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
    Represents a list of SeriesInstanceUIDs pertaining to a SR
    referenced in an SR file
    """

    pass


class SR_RefSOPs(list):  # noqa
    """
    Represents a list of SOPInstanceUIDs pertaining to a SR
    referenced in an SR file
    """

    pass


def sr_reference_uids(
    sr: DicomInput,
) -> tuple[SR_RefSeries, SR_RefSOPs] | None:
    """Get the ReferencedSeriesInstanceUIDs from an SR file

    We assume SR only references a `RTSTRUCT` file.

    Since we might need to match on SOP Instance UIDs if the reference is
    a MR, we also get the SOP Instance UIDs

    """
    sr = load_dicom(sr)
    if not "CurrentRequestedProcedureEvidenceSequence" in sr:
        return None

    series_uids = set()
    sop_uids = set()

    for evidence_seq in sr.CurrentRequestedProcedureEvidenceSequence:
        for series_seq in evidence_seq.ReferencedSeriesSequence:
            series_uids.add(series_seq.SeriesInstanceUID)
            for ref_seq in series_seq.ReferencedSOPSequence:
                sop_uids.add(ref_seq.ReferencedSOPInstanceUID)

    series_list = SR_RefSeries(series_uids)
    sop_list = SR_RefSOPs(sop_uids)

    return series_list, sop_list
