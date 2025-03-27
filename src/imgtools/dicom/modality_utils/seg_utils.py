from typing import TYPE_CHECKING

from pydicom.dataset import FileDataset

from imgtools.dicom.dicom_reader import DicomInput, load_seg_dcm

if TYPE_CHECKING:
    from pydicom.dataset import FileDataset

__all__ = [
    "seg_reference_uids",
    "SEGRefSeries",
    "SEGRefSOPs",
]


class SEGRefSeries(str):
    """A single string to store the ReferencedSeriesInstanceUID for a SEG file"""

    pass


class SEGRefSOPs(list):
    """A list representing all the ReferencedSOPInstanceUIDs for a SEG file"""

    pass


def seg_reference_uids(
    segdcm: DicomInput,
) -> tuple[SEGRefSeries, SEGRefSOPs] | SEGRefSOPs | None:
    """Get the ReferencedSeriesInstanceUID or ReferencedSOPInstanceUIDs from a SEG file

    Modern Segmentation objects have a `ReferencedSeriesSequence` attribute
    which contains the `SeriesInstanceUID` of the referenced series and
    a `ReferencedInstanceSequence` attribute which contains the SOPInstanceUIDs
    of the referenced instances.

    Older Segmentation objects have a `SourceImageSequence` attribute which
    only contains the `SOPInstanceUIDs` of the referenced instances.

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
                " This is unexpected and may cause issues. "
                f"Found {len(ref_series)} ReferencedSeriesInstanceUIDs."
            )
            raise ValueError(errmsg)
    elif "SourceImageSequence" in seg:
        ref_sop = SEGRefSOPs(
            [seq.ReferencedSOPInstanceUID for seq in seg.SourceImageSequence]
        )
        return ref_sop

    return None
