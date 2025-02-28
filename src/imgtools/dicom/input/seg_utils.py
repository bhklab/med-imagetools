from typing import TYPE_CHECKING

from pydicom.dataset import FileDataset

from imgtools.dicom.input.dicom_reader import DicomInput, load_seg_dcm

if TYPE_CHECKING:
    from pydicom.dataset import FileDataset

__all__ = [
    "seg_reference_uids",
    "SEGRefSeries",
    "SEGRefSOPs",
]


class SEGRefSeries(str):
    pass


class SEGRefSOPs(list):
    pass


def seg_reference_uids(
    segdcm: DicomInput,
) -> tuple[SEGRefSeries, SEGRefSOPs] | SEGRefSOPs | None:
    """Get the ReferencedSeriesInstanceUID or ReferencedSOPInstanceUIDs from a SEG file

    Modern Segmentation objects have a ReferencedSeriesSequence attribute
    which contains the SeriesInstanceUID of the referenced series and
    a ReferencedInstanceSequence attribute which contains the SOPInstanceUIDs
    of the referenced instances.

    Older Segmentation objects have a SourceImageSequence attribute which
    only contains the SOPInstanceUIDs of the referenced instances.

    Parameters
    ----------
    segdcm : FileDataset | str | Path | bytes
        Input DICOM file as a `pydicom.FileDataset`, file path, or byte stream.

    Returns
    -------
    tuple[SEGRefSeries, SEGRefSOPs] | SEGRefSOPs | None
        If the ReferencedSeriesSequence is present, return a tuple of
        the ReferencedSeriesInstanceUID and ReferencedSOPInstanceUIDs.

        OR if the SourceImageSequence is present, return the ReferencedSOPInstanceUIDs.

        OR if neither are present, return None.

    Examples
    --------
    match seg_reference_uids("/path/to/SEG.dcm"):
        case None:
            print("No ReferencedSeriesInstanceUID or ReferencedSOPInstanceUIDs")
        case ref_series, ref_sop:
            print(f"ReferencedSeriesInstanceUID: {ref_series}")
            print(f"ReferencedSOPInstanceUIDs: {ref_sop}")
        case ref_sop:
            print(f"ReferencedSOPInstanceUIDs: {ref_sop}")
    """

    seg: FileDataset = load_seg_dcm(segdcm)

    if "ReferencedSeriesSequence" in seg:
        ref_series = [
            SEGRefSeries(ref_series.SeriesInstanceUID)
            for ref_series in seg.ReferencedSeriesSequence
        ]
        ref_sop = SEGRefSOPs(
            [
                seq.ReferencedSOPInstanceUID
                for seq in seg.ReferencedSeriesSequence[
                    0
                ].ReferencedInstanceSequence
            ]
        )
        # Check if there is only one ReferencedSeriesInstanceUID
        if len(ref_series) == 1:
            return ref_series[0], ref_sop
        else:
            errmsg = (
                "Multiple ReferencedSeriesInstanceUIDs found in ReferencedSeriesSequence"
                "This is unexpected and may cause issues."
                f"Found {len(ref_series)} ReferencedSeriesInstanceUIDs"
            )
            raise ValueError(errmsg)
    elif "SourceImageSequence" in seg:
        ref_sop = SEGRefSOPs(
            [seq.ReferencedSOPInstanceUID for seq in seg.SourceImageSequence]
        )
        return ref_sop

    return None


if __name__ == "__main__":
    from rich import print  # type: ignore # noqa

    ps = [
        "/home/gpudual/bhklab/radiomics/Projects/med-imagetools/testdata/ISPY2-111038/SEG_Series-94849/00000001.dcm",
        "/home/gpudual/bhklab/radiomics/Projects/med-imagetools/testdata/LUNG1-001/SEG_Series-9.554/00000001.dcm",
        "/home/gpudual/bhklab/radiomics/Projects/med-imagetools/testdata/Adrenal_Ki67_Seg_002/SEG_Series-67488/00000001.dcm",
        "/home/gpudual/bhklab/radiomics/Projects/med-imagetools/testdata/LIDC-IDRI-0340/SEG_Series-50648/00000001.dcm",
        "/home/gpudual/bhklab/radiomics/Projects/med-imagetools/testdata/PCAMPMRI-00002/SEG_Series-23.52/00000001.dcm",
        "/home/gpudual/bhklab/radiomics/Projects/med-imagetools/testdata/R01-050/SEG_Series-51215/00000001.dcm",
    ]
    for p in ps:
        match seg_reference_uids(p):
            case None:
                print(
                    "No ReferencedSeriesInstanceUID or ReferencedSOPInstanceUIDs"
                )
            case ref_series, ref_sop:
                print(f"ReferencedSeriesInstanceUID: {ref_series}")
                print(f"ReferencedSOPInstanceUIDs: {ref_sop}")
            case ref_sop:
                print(f"ReferencedSOPInstanceUIDs: {ref_sop}")
