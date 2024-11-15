from pathlib import Path
from typing import List

from pydicom.misc import is_dicom

from imgtools.logging import logger  # Custom logger for debugging


def _check_file(file: Path, check_header: bool) -> bool:
	"""
	Helper function to validate a file based on the `check_header` flag.

	Parameters
	----------
	file : Path
	    The file to check.
	check_header : bool
	    If True, check the file's DICOM header.

	Returns
	-------
	bool
	    True if the file is valid based on the criteria.
	"""
	if check_header:
		return is_dicom(file)  # Perform header validation for DICOM
	else:
		return file.is_file()  # Ensure it's a file (not a directory)


def find_dicoms(
	directory: Path,
	case_sensitive: bool,
	recursive: bool,
	check_header: bool,
	extension: str = 'dcm',
) -> List[Path]:
	"""
	Find DICOM files in a directory.

	This function searches for files with a specified extension in the
	provided directory. It can optionally perform a recursive search
	through subdirectories and validate the files by checking their
	DICOM headers. The case sensitivity of the search can also be
	controlled.

	Parameters
	----------
	directory : Path
	    The directory in which to search for DICOM files.
	case_sensitive : bool
	    If True, perform a case-sensitive search for the file extension.
	    If False, the search will ignore case differences in file extensions.
	recursive : bool
	    If True, perform a recursive search (search in subdirectories).
	    If False, only search in the provided directory.
	check_header : bool
	    If True, validate files by checking for a valid DICOM header ('DICM')
	    after the preamble. This option ensures files are valid DICOMs but
	    can slow down the search.
	extension : str, optional
	    The file extension to search for. Default is 'dcm'.

	Returns
	-------
	List[Path]
	    A list of file paths to the DICOM files found during the search.
	"""

	# Log the start of the DICOM search for debugging purposes

	# Define the file search pattern
	# If case-sensitive, create patterns for both lower and upper case extensions
	pattern = f'*.{extension}'
	if case_sensitive:
		pattern = f'*.{extension.lower()}|*.{extension.upper()}'

	# Choose the appropriate globbing method based on recursion
	# rglob is used for recursive search, glob for non-recursive

	glob_method = directory.rglob if recursive else directory.glob

	logger.debug(
		'Looking for DICOM files',
		directory=directory,
		recursive=recursive,
		search_pattern=pattern,
		check_header=check_header,
	)

	# Return the resolved file paths that match the pattern and criteria
	return [
		file.resolve()
		for file in glob_method(pattern)  # Iterate over matching files
		if _check_file(file, check_header)  # Validate each file
	]
