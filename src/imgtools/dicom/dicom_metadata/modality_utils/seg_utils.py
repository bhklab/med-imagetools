from pydicom.dataset import Dataset

__all__ = [
    "seg_reference_uids",
    "SEGRefSeries",
    "SEGRefSOPs",
]


class SEGRefSeries(str):
    """A single string to store the ReferencedSeriesInstanceUID for a SEG file"""

    pass


class SEGRefSOPs(list[str]):
    """A list representing all the ReferencedSOPInstanceUIDs for a SEG file"""

    pass


def seg_reference_uids(
    seg: Dataset,
) -> tuple[SEGRefSeries, SEGRefSOPs]:
    """Get the ReferencedSeriesInstanceUID or ReferencedSOPInstanceUIDs from a SEG file

    Modern Segmentation objects have a `ReferencedSeriesSequence` attribute
    which contains the `SeriesInstanceUID` of the referenced series and
    a `ReferencedInstanceSequence` attribute which contains the SOPInstanceUIDs
    of the referenced instances.

    Older Segmentation objects have a `SourceImageSequence` attribute which
    only contains the `SOPInstanceUIDs` of the referenced instances.

    Parameters
    ----------
    seg : Dataset
        Input DICOM segmentation object as a pydicom Dataset.

    Returns
    -------
    tuple[SEGRefSeries, SEGRefSOPs]
        Always returns a tuple containing:
        - ReferencedSeriesInstanceUID (empty string if not available)
        - ReferencedSOPInstanceUIDs (empty list if not available)
    """

    assert seg.Modality == "SEG", (
        "Input DICOM file is not a Segmentation object"
    )

    if "ReferencedSeriesSequence" in seg:
        ref_series: list[SEGRefSeries] = [
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
        ref_sop_list = [
            seq.ReferencedSOPInstanceUID for seq in seg.SourceImageSequence
        ]

        return SEGRefSeries(""), SEGRefSOPs(ref_sop_list)

    # Return empty values if no reference information is found
    return SEGRefSeries(""), SEGRefSOPs([])


def get_seg_spacing(seg: Dataset) -> list[float] | None:
    """
    Get the pixel spacing and slice spacing or thickness from a SEG file.

    Parameters
    ----------
    seg : Dataset
        Input DICOM segmentation object as a pydicom Dataset.

    Returns
    -------
    list[float] | None
        A list of three floats representing [x_spacing, y_spacing, z_spacing] if available,
        or None if the spacing information is not found.
    """
    if not (
        (sharedseq := seg.SharedFunctionalGroupsSequence)
        and (pms := sharedseq[0].PixelMeasuresSequence)
        and (pixelspacing := pms[0].PixelSpacing)
        and (
            spacing := pms[0].get("SpacingBetweenSlices")
            or pms[0].get("SliceThickness")
        )
    ):
        return None

    return [
        float(pixelspacing[0]),
        float(pixelspacing[1]),
        float(spacing),
    ]


def get_seg_direction(seg: Dataset) -> list[float] | None:
    """
    Get the direction cosines (orientation) from a SEG file.

    Parameters
    ----------
    seg : Dataset
        Input DICOM segmentation object as a pydicom Dataset.

    Returns
    -------
    list[float] | None
        A list of six floats representing the direction cosines if available,
        or None if the orientation information is not found.
    """
    if not (
        (sharedseq := seg.SharedFunctionalGroupsSequence)
        and (pos := sharedseq[0].PlaneOrientationSequence)
        and (direction := pos[0].get("ImageOrientationPatient"))
    ):
        return None
    return [float(v) for v in direction]
