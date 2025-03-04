from __future__ import annotations

from typing import TYPE_CHECKING

from pydicom.dataset import FileDataset

from imgtools.dicom.input.dicom_reader import DicomInput, load_seg_dcm

if TYPE_CHECKING:
    from pydicom.dataset import FileDataset

__all__ = [
    "seg_reference_uids",
    "SEGRefSeries",
    "SEGRefSOPs",
    "MultipleReferencedSeriesError",
    "NoSegmentationReferencesError",
]


class MultipleReferencedSeriesError(Exception):
    """Exception raised when a SEG file contains multiple ReferencedSeriesInstanceUIDs"""

    def __init__(self, count: int) -> None:
        self.message = (
            "Multiple ReferencedSeriesInstanceUIDs found in ReferencedSeriesSequence"
            " This is unexpected and may cause issues. "
            f"Found {count} ReferencedSeriesInstanceUIDs."
        )
        super().__init__(self.message)


class NoSegmentationReferencesError(Exception):
    """Exception raised when a SEG file does not contain any references to source images"""

    def __init__(self, seg_identifier: str | FileDataset) -> None:
        self.seg_identifier = seg_identifier
        self.message = f"SEG file: {seg_identifier} does not contain ReferencedSeriesSequence or SourceImageSequence"
        super().__init__(self.message)


class SEGRefSeries(str):
    """A single string to store the ReferencedSeriesInstanceUID for a SEG file"""

    pass


class SEGRefSOPs(list):
    """A list representing *all* the ReferencedSOPInstanceUIDs for a SEG file"""

    pass


def seg_reference_uids(
    segdcm: DicomInput,
) -> tuple[SEGRefSeries, SEGRefSOPs] | SEGRefSOPs:
    """Get the ReferencedSeriesInstanceUID or ReferencedSOPInstanceUIDs from a SEG file

    Notes
    -----
    Modern Segmentation objects have a `ReferencedSeriesSequence` attribute
    which contains the `SeriesInstanceUID` of the referenced series and
    a `ReferencedInstanceSequence` attribute which contains the `SOPInstanceUIDs`
    of the referenced instances.

    Older Segmentation objects have a `SourceImageSequence` (ISPY2) attribute which
    only contains the `SOPInstanceUIDs` of the referenced instances.

    Parameters
    ----------
    segdcm : FileDataset | str | Path | bytes
        Input DICOM file as a `pydicom.FileDataset`, file path, or byte stream.

    Returns
    -------
    tuple[SEGRefSeries, SEGRefSOPs] | SEGRefSOPs
        If the ReferencedSeriesSequence is present, return a tuple of
        the ReferencedSeriesInstanceUID and ReferencedSOPInstanceUIDs.

        OTHE if the SourceImageSequence is present, return the ReferencedSOPInstanceUIDs.

    Raises
    ------
    MultipleReferencedSeriesException
        If the SEG file contains multiple ReferencedSeriesInstanceUIDs
    NoSegmentationReferencesException
        If the SEG file does not contain ReferencedSeriesSequence or SourceImageSequence

    Examples
    --------
    match seg_reference_uids("/path/to/SEG.dcm"):
        case case SEGRefSeries(ref_series), SEGRefSOPs(ref_sop):
            print(f"ReferencedSeriesInstanceUID: {ref_series}")
            print(f"ReferencedSOPInstanceUIDs: {ref_sop}")
        case SEGRefSOPs(ref_sop):
            print(f"No Referenced SeriesUIDs found. ReferencedSOPInstanceUIDs: {ref_sop}")
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
            raise MultipleReferencedSeriesError(len(ref_series))
    elif "SourceImageSequence" in seg:
        ref_sop = SEGRefSOPs(
            [seq.ReferencedSOPInstanceUID for seq in seg.SourceImageSequence]
        )
        return ref_sop
    else:
        raise NoSegmentationReferencesError(str(seg.filename))


if __name__ == "__main__":
    from pathlib import Path

    from tqdm import tqdm

    from imgtools.dicom.find_dicoms import find_dicoms

    seg_paths = find_dicoms(
        Path("testdata").expanduser(),
        recursive=True,
        check_header=False,
        extension="dcm",
        search_input=["SEG_Series"],
    )

    series_uid_list = []
    sop_uid_list: list[str] = []
    for path in tqdm(seg_paths):
        match seg_reference_uids(path):
            case SEGRefSeries(ref_series), SEGRefSOPs(ref_sop):
                series_uid_list.append(ref_series)
            case SEGRefSOPs(ref_sop):
                sop_uid_list.extend(ref_sop)

    # print table of # of series_uids and sop_uids
