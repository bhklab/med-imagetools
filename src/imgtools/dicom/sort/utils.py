"""DICOM Sorting Utilities.

This module provides utilities for truncating UIDs,
and reading specific tags from DICOM files.

Functions
---------
truncate_uid(uid: str, last_digits: int = 5) -> str
    Truncate a UID to the last n characters.
read_tags(file: Path, tags: list[str], truncate: bool = True) -> dict[str, str]
    Read specified tags from a DICOM file.

Examples
--------
Truncate a UID:
    >>> truncate_uid(
    ...     "1.2.840.10008.1.2.1",
    ...     last_digits=5,
    ... )
    '.1.2.1'

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

from pydicom import dcmread
from pydicom.errors import InvalidDicomError


def truncate_uid(uid: str, last_digits: int = 5) -> str:
    """
    Truncate the UID to the last n characters (including periods and underscores).

    If the UID is shorter than `last_digits`, the entire UID is returned.

    Parameters
    ----------
    uid : str
        The UID string to truncate.
    last_digits : int, optional
        The number of characters to keep at the end of the UID (default is 5).

    Returns
    -------
    str
        The truncated UID string.

    Examples
    --------
    >>> truncate_uid(
    ...     "1.2.840.10008.1.2.1",
    ...     last_digits=5,
    ... )
    '.1.2.1'
    >>> truncate_uid(
    ...     "12345",
    ...     last_digits=10,
    ... )
    '12345'
    """
    assert uid is not None
    assert isinstance(uid, str)
    assert isinstance(last_digits, int)
    if last_digits >= len(uid) or last_digits <= 0:
        return uid

    return uid[-last_digits:]


def read_tags(
    file: Path,
    tags: List[str],
    truncate: int = 5,
    default: Optional[str] = "",
    force: bool = False,
) -> Dict[str, str]:
    """
    Extracts specified DICOM tags from a file.
    
    Reads a DICOM file and returns a dictionary mapping each requested tag to its
    value. For tags ending with "UID", the value is truncated to the last `truncate`
    characters if `truncate` is positive; otherwise, the full UID is retained.
    Missing tags are assigned the specified default value (with RTSTRUCT files defaulting
    the missing 'InstanceNumber' to '1').
    
    Parameters:
        file (Path): Path to the DICOM file.
        tags (List[str]): List of DICOM tags to extract.
        truncate (int, optional): Number of characters to keep from the end of UID strings.
            A non-positive value disables truncation (default is 5).
        default (Optional[str], optional): Value assigned to missing tags (default is "").
        force (bool, optional): If True, attempts to read the file even if it is not a valid
            DICOM file (default is False).
    
    Returns:
        Dict[str, str]: A dictionary where keys are tag names and values are their extracted values.
    
    Raises:
        FileNotFoundError: If the file does not exist.
        InvalidDicomError: If the file is not a valid DICOM file.
        ValueError: If an error occurs while reading the file.
    
    Examples:
        Extract tags with UID truncation:
            >>> from pathlib import Path
            >>> read_tags(Path("sample.dcm"), ["PatientID", "StudyInstanceUID"])
            {'PatientID': '12345', 'StudyInstanceUID': '1.2.3.4.5'}
    
        Extract tags without UID truncation:
            >>> read_tags(Path("sample.dcm"), ["PatientID", "StudyInstanceUID"], truncate=0)
            {'PatientID': '12345', 'StudyInstanceUID': '1.2.840.10008.1.2.1'}
    
        Handle missing tags:
            >>> read_tags(Path("sample.dcm"), ["NonexistentTag"])
            {'NonexistentTag': 'UNKNOWN'}
    """
    assert isinstance(file, Path)
    assert (
        isinstance(tags, list)
        and all(isinstance(tag, str) for tag in tags)
        and tags is not None
    )

    try:
        dicom = dcmread(
            file, specific_tags=tags, stop_before_pixels=True, force=force
        )
    except FileNotFoundError as fnfe:
        errmsg = f"File not found: {file}"
        raise FileNotFoundError(errmsg) from fnfe
    except InvalidDicomError as ide:
        errmsg = f"Invalid DICOM file: {file}"
        raise InvalidDicomError(errmsg) from ide
    except ValueError as ve:
        errmsg = f"Value error reading DICOM file: {file}"
        raise ValueError(errmsg) from ve

    result = {}

    for tag in tags:
        value = str(dicom.get(tag, default=default))

        if tag.endswith("UID") and truncate > 0:
            value = truncate_uid(value, last_digits=truncate)

        result[tag] = value
    return result
