"""DICOM Sorting Utilities.

This module provides utilities for truncating UIDs,
and reading specific tags from DICOM files.

Functions
---------
read_tags(file: Path, tags: list[str], truncate: bool = True) -> dict[str, str]
    Read specified tags from a DICOM file.

Examples
--------
Read tags from a DICOM file:
    >>> from pathlib import (
    ...     Path,
    ... )
    >>> tags = [
    ...     "PatientID",
    ...     "StudyInstanceUID",
    ... ]
    >>> read_tags(
    ...     Path("sample.dcm"),
    ...     tags,
    ... )
    {'PatientID': '12345', 'StudyInstanceUID': '1.2.3.4.5'}
"""

from pathlib import Path
from typing import Dict, List, Optional

from imgtools.dicom import load_dicom
from imgtools.utils import truncate_uid


def read_tags(
    file: Path,
    tags: List[str],
    truncate: int = 5,
    default: Optional[str] = "",
    force: bool = False,
) -> Dict[str, str]:
    """
    Read the specified tags from a DICOM file.

    Reads a set of tags from a DICOM file and applies optional sanitization
    and truncation for UIDs. Handles cases where specific tags may be missing.

    Parameters
    ----------
    file : Path
        Path to the DICOM file.
    tags : list of str
        List of DICOM tags to read.
    truncate : int, optional
        Number of characters to keep at the end of UIDs (default is 5).
        0 or negative values will keep the entire UID.
    default : str, optional
        Default value to use for missing tags (default is "").
    force : bool, optional
        If True, force reading the file even if it is not a valid DICOM file
        (default is False).

    Returns
    -------
    dict of str : str
        A dictionary mapping tags to their values.

    Raises
    ------
    TypeError
        If there is a type error while reading the DICOM file.
    InvalidDicomError
        If the file is not a valid DICOM file.
    ValueError
        If there is a value error while reading the file.

    Notes
    -----
    For RTSTRUCT files, missing 'InstanceNumber' tags default to '1'.

    Examples
    --------
    Read tags from a valid DICOM file with truncation:
    >>> from pathlib import (
    ...     Path,
    ... )
    >>> read_tags(
    ...     Path("sample.dcm"),
    ...     [
    ...         "PatientID",
    ...         "StudyInstanceUID",
    ...     ],
    ... )
    {'PatientID': '12345', 'StudyInstanceUID': '1.2.3.4.5'}

    Read tags without truncating UIDs:
    >>> read_tags(
    ...     Path("sample.dcm"),
    ...     [
    ...         "PatientID",
    ...         "StudyInstanceUID",
    ...     ],
    ...     truncate=False,
    ... )
    {'PatientID': '12345', 'StudyInstanceUID': '1.2.840.10008.1.2.1'}

    Handle missing tags:
    >>> read_tags(
    ...     Path("sample.dcm"),
    ...     ["NonexistentTag"],
    ... )
    [warn] No value for tag: NonexistentTag in file: sample.dcm
    {'NonexistentTag': 'UNKNOWN'}
    """
    assert isinstance(file, Path)
    assert (
        isinstance(tags, list)
        and all(isinstance(tag, str) for tag in tags)
        and tags is not None
    )

    dicom = load_dicom(
        file, force=force, stop_before_pixels=True, specific_tags=tags
    )

    result = {}

    for tag in tags:
        value = str(dicom.get(tag, default=default))

        if tag.endswith("UID") and truncate > 0:
            value = truncate_uid(value, last_digits=truncate)

        result[tag] = value
    return result
