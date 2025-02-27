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
            SeriesInstanceUID = str,
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


if __name__ == "__main__":
    from pathlib import Path

    from rich import print  # type: ignore # noqa
    from rich.table import Table

    ps = [
        "testdata/PCAMPMRI-00001/SR_Series-8.730/00000001.dcm",
        "testdata/PCAMPMRI-00001/SR_Series-9.297/00000001.dcm",
        "testdata/OCT-01-1271/SR_Series-72387/IM-0229-0005.dcm",
        "testdata/OCT-01-0102/SR_Series-97096/IM-0032-0005.dcm",
        "testdata/LIDC-IDRI-0340/SR_Series-66150/00000001.dcm",
        "testdata/OCT-01-1191/SR_Series-12663/IM-0299-0006.dcm",
        "testdata/OCT-01-1070/SR_Series-28223/IM-0333-0004-0002.dcm",
        "testdata/OCT-01-1125/SR_Series-50474/IM-0289-0004-0002.dcm",
    ]
    table = Table(title="Reference UIDs for SR Files")
    table.add_column("PatientID")
    table.add_column("File")
    table.add_column("Reference Series Instance UIDs Count")
    table.add_column("Reference SOP Instance UIDs Count")

    for p in ps:
        res = sr_reference_uids(p)
        if res:
            series_uids, sop_uids = res
            table.add_row(
                Path(p).parent.parent.name,
                Path(p).name,
                str(len(series_uids)),
                str(len(sop_uids)),
            )

    print(table)
