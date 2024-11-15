from pathlib import Path
from typing import List

from imgtools.logging import logger


def find_dicoms(
	directory: Path,
	extension: str = 'dcm',
	case_sensitive: bool = False,
	recursive: bool = True,
) -> List[Path]:
	"""Find DICOM files in a directory.

	This function searches through the provided directory and its
	subdirectories to locate files with the specified extension. The
	search can be made case-sensitive based on the parameter settings.
	Only files (not directories) matching the criteria are returned.

	Parameters
	----------
	directory : Path
		The directory in which to begin the search for DICOM files.
	extension : str, optional
		The file extension to look for, by default 'dcm'.
	case_sensitive : bool, optional
		If True, the search will be case-sensitive, by default False.
	recursive : bool, optional
		If True, the search will be recursive using rglob, by default True.

	Returns
	-------
	List[Path]
		A list of file paths that match the given extension criteria.

	"""
	logger.debug('Looking for DICOM files', directory=directory)

	pattern = f'*.{extension}'
	if case_sensitive:
		pattern = f'*.{extension.lower()}|*.{extension.upper()}'

	glob_method = directory.rglob if recursive else directory.glob

	return [file.resolve() for file in glob_method(pattern) if file.is_file()]
