"""
DICOM Utilities.

This module provides utilities for:
- Searching and validating DICOM files in directories.
- Looking up DICOM tags by keywords with optional hexadecimal formatting.
- Checking the existence of DICOM tags.
- Finding similar DICOM tags.

Examples
--------
Find DICOM files in a directory:
    >>> from pathlib import Path
    >>> from imgtools.dicom.utils import find_dicoms
    >>> files = find_dicoms(Path('/data/dicoms'), recursive=True, check_header=True)
    >>> len(files)
    10

Lookup a DICOM tag:
    >>> from imgtools.dicom.utils import lookup_tag
    >>> lookup_tag('PatientID')
    '1048608'
    >>> lookup_tag('PatientID', hex_format=True)
    '0x100020'

Find similar DICOM tags:
    >>> from imgtools.dicom.utils import similar_tags
    >>> similar_tags('PatinetID')  # Misspelled keyword
    ['PatientID', 'PatientName', 'PatientBirthDate']
"""

import difflib
import functools
from pathlib import Path
from typing import FrozenSet, List, Optional

from pydicom._dicom_dict import DicomDictionary
from pydicom.datadict import dictionary_has_tag, tag_for_keyword
from pydicom.misc import is_dicom

from imgtools.logging import logger


def _is_valid_dicom(file: Path, check_header: bool) -> bool:
	"""
	Notes
	-----
	Validation includes:
	- Ensuring the file is a valid DICOM file (if `check_header` is True).
	- Ensuring the file exists and is not a directory (if `check_header` is False).
	"""
	if check_header:
		return is_dicom(file)
	return file.is_file()


def find_dicoms(
	directory: Path,
	recursive: bool,
	check_header: bool,
	extension: str = 'dcm',
) -> List[Path]:
	"""
	Find DICOM files in a directory.

	This function searches for files with a specified extension in the provided directory.
	It supports recursive search and optional DICOM header validation.

	Parameters
	----------
	directory : Path
	    Directory to search for DICOM files.
	recursive : bool
	    If True, search subdirectories recursively.
	    If False, search only the specified directory.
	check_header : bool
	    If True, validate files by checking for a valid DICOM header.
	extension : str, optional
	    File extension to search for (default is 'dcm').

	Returns
	-------
	List[Path]
	    List of file paths to valid DICOM files.

	Notes
	-----
	- If `check_header` is True, this function may be slower due to header validation.

	Examples
	--------
	Find DICOM files with header validation:
	    >>> from pathlib import Path
	    >>> find_dicoms(Path('/data'), recursive=True, check_header=True)
	    [PosixPath('/data/scan1.dcm'), PosixPath('/data/scan2.dcm')]

	Find files without recursive search:
	    >>> find_dicoms(Path('/data'), recursive=False, check_header=False)
	    [PosixPath('/data/scan1.dcm')]
	"""
	pattern = f'*.{extension}'

	glob_method = directory.rglob if recursive else directory.glob

	logger.debug(
		'Looking for DICOM files',
		directory=directory,
		recursive=recursive,
		search_pattern=pattern,
		check_header=check_header,
	)

	return [file.resolve() for file in glob_method(pattern) if _is_valid_dicom(file, check_header)]


###############################################################################
# DICOM TAG UTILITIES
###############################################################################

ALL_DICOM_TAGS: FrozenSet[str] = frozenset(value[4] for value in DicomDictionary.values())


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
	    >>> lookup_tag('PatientID')
	    '1048608'

	Lookup a DICOM tag in hexadecimal format:
	    >>> lookup_tag('PatientID', hex_format=True)
	    '0x100020'
	"""
	if (tag := tag_for_keyword(keyword)) is None:
		return None
	return f'0x{tag:X}' if hex_format else str(tag)


@functools.lru_cache(maxsize=1024)
def tag_exists(keyword: str) -> bool:
	"""
	Check if a DICOM tag exists for a given keyword.

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
	>>> tag_exists('PatientID')
	True
	>>> tag_exists('InvalidKeyword')
	False
	"""
	return dictionary_has_tag(keyword)


@functools.lru_cache(maxsize=1024)
def similar_tags(keyword: str, n: int = 3, threshold: float = 0.6) -> List[str]:
	"""
	Find similar DICOM tags for a given keyword.

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
	    >>> similar_tags('PatinetID')
	    ['PatientID', 'PatientName', 'PatientBirthDate']s

	Adjust the number of results and threshold:
	    >>> similar_tags('PatinetID', n=5, threshold=0.7)
	    ['PatientID', 'PatientName']
	"""
	return difflib.get_close_matches(keyword, ALL_DICOM_TAGS, n, threshold)
