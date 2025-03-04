"""
DICOM Utilities.

This module provides utilities for:
- Searching and validating DICOM files in directories.
- Looking up DICOM tags by keywords with optional hexadecimal formatting.
- Checking the existence of DICOM tags.
- Finding similar DICOM tags.
"""

import difflib
import functools
from typing import FrozenSet, List, Optional

from pydicom._dicom_dict import DicomDictionary
from pydicom.datadict import dictionary_has_tag, tag_for_keyword

###############################################################################
# DICOM TAG UTILITIES
###############################################################################

ALL_DICOM_TAGS: FrozenSet[str] = frozenset(
    value[4] for value in DicomDictionary.values()
)


@functools.lru_cache(maxsize=1024)
def lookup_tag(keyword: str, hex_format: bool = False) -> Optional[str]:
    """
    Lookup the tag for a given DICOM keyword.

    Parameters
    ----------
    keyword : str
        The DICOM keyword to look up.
    hex_format : bool, optional
        If True, return the tag in hexadecimal format (default is False).

    Returns
    -------
    str or None
        The DICOM tag as a string, or None if the keyword is invalid.

    Examples
    --------

    Lookup a DICOM tag in decimal format:

    >>> lookup_tag("PatientID")
    '1048608'

    Lookup a DICOM tag in hexadecimal format:

    >>> lookup_tag(
    ...     "PatientID",
    ...     hex_format=True,
    ... )
    '0x100020'
    """
    if (tag := tag_for_keyword(keyword)) is None:
        return None
    return f"0x{tag:X}" if hex_format else str(tag)


@functools.lru_cache(maxsize=1024)
def tag_exists(keyword: str) -> bool:
    """Boolean check if a DICOM tag exists for a given keyword.

    Parameters
    ----------
    keyword : str
        The DICOM keyword to check.

    Returns
    -------
    bool
        True if the tag exists, False otherwise.

    Examples
    --------

    >>> tag_exists("PatientID")
    True

    >>> tag_exists("InvalidKeyword")
    False
    """
    return dictionary_has_tag(keyword)


@functools.lru_cache(maxsize=1024)
def similar_tags(
    keyword: str, n: int = 3, threshold: float = 0.6
) -> List[str]:
    """Find similar DICOM tags for a given keyword.

    Useful for User Interface to suggest similar tags based on a misspelled keyword.

    Parameters
    ----------
    keyword : str
        The keyword to search for similar tags.
    n : int, optional
        Maximum number of similar tags to return (default is 3).
    threshold : float, optional
        Minimum similarity ratio (default is 0.6).

    Returns
    -------
    List[str]
        A list of up to `n` similar DICOM tags.

    Examples
    --------
    Find similar tags for a misspelled keyword:

    >>> similar_tags("PatinetID")
    ['PatientID', 'PatientName', 'PatientBirthDate']

    Adjust the number of results and threshold:

    >>> similar_tags(
    ...     "PatinetID",
    ...     n=5,
    ...     threshold=0.7,
    ... )
    ['PatientID', 'PatientName']
    """
    return difflib.get_close_matches(keyword, ALL_DICOM_TAGS, n, threshold)
