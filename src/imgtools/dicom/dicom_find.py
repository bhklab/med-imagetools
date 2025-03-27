from itertools import islice
from pathlib import Path
from typing import List

from pydicom.misc import is_dicom

from imgtools.logging import logger


def _is_valid_dicom(file: Path, check_header: bool) -> bool:
    """
    Determines if a file is valid as a DICOM.
    
    If `check_header` is True, the file must exist (and not be a directory) and pass a DICOM header check.
    If `check_header` is False, only the file’s existence as a regular file is verified.
    """
    if check_header:
        return is_dicom(file) and file.is_file()
    return file.is_file()


def find_dicoms(
    directory: Path,
    recursive: bool = True,
    check_header: bool = False,
    extension: str | None = None,
    limit: int | None = None,
    search_input: List[str] | None = None,
) -> List[Path]:
    """Locate DICOM files in a specified directory.

    This function scans a directory for files matching the specified extension
    and validates them as DICOM files based on the provided options. It supports
    recursive search and optional header validation to confirm file validity.

    Parameters
    ----------
    directory : Path
        The directory in which to search for DICOM files.
    recursive : bool
        Whether to include subdirectories in the search
    check_header : bool
        Whether to validate files by checking for a valid DICOM header.
            - If `True`, perform DICOM header validation (slower but more accurate).
            - If `False`, skip header validation and rely on extension.
    extension : str, optional
        File extension to search for (e.g., "dcm"). If `None`, consider all files
        regardless of extension.
    limit : int, optional
        Maximum number of DICOM files to return. If `None`, return all found files.
    search_input : List[str], optional
        List of terms to filter files by. Only files containing all terms
        in their paths will be included. If `None`, no filtering is applied.

    Returns
    -------
    List[Path]
        A list of valid DICOM file paths found in the directory.

    Notes
    -----
    - If `check_header` is enabled, the function checks each file for a valid
        DICOM header, which may slow down the search process.

    Examples
    --------
    Setup

    >>> from pathlib import Path
    >>> from imgtools.dicom.dicom_find import find_dicoms

    Find DICOM files recursively without header validation:

    >>> find_dicoms(
    ...     Path("/data"),
    ...     recursive=True,
    ...     check_header=False,
    ... )
    [PosixPath('/data/scan1.dcm'), PosixPath('/data/subdir/scan2.dcm'), \
PosixPath('/data/subdir/scan3.DCM')]

    Suppose that `scan3.DCM` is not a valid DICOM file. Find DICOM files with \
header validation:

    >>> find_dicoms(
    ...     Path("/data"),
    ...     recursive=True,
    ...     check_header=True,
    ... )
    [PosixPath('/data/scan1.dcm'), PosixPath('/data/subdir/scan2.dcm')]

    Find DICOM files without recursion:
    >>> find_dicoms(
    ...     Path("/data"),
    ...     recursive=False,
    ...     check_header=False,
    ... )
    [PosixPath('/data/scan1.dcm')]

    Find DICOM files with a specific extension:
    >>> find_dicoms(
    ...     Path("/data"),
    ...     recursive=True,
    ...     check_header=False,
    ...     extension="dcm",
    ... )
    [PosixPath('/data/scan1.dcm'), PosixPath('/data/subdir/scan2.dcm')]

    Find DICOM files with a search input (substring match):
    >>> find_dicoms(
    ...     Path("/data"),
    ...     recursive=True,
    ...     check_header=False,
    ...     search_input=["1", "scan2"],
    ... )
    [PosixPath('/data/scan1.dcm'), PosixPath('/data/subdir/scan2.dcm')]

    Find DICOM files with a limit:
    >>> find_dicoms(
    ...     Path("/data"),
    ...     recursive=True,
    ...     check_header=False,
    ...     limit=1,
    ... )
    [PosixPath('/data/scan1.dcm')]

    Find DICOM files with all options:
    >>> find_dicoms(
    ...     Path("/data"),
    ...     recursive=True,
    ...     check_header=True,
    ...     extension="dcm",
    ...     limit=2,
    ...     search_input=["scan"],
    ... )
    [PosixPath('/data/scan1.dcm'), PosixPath('/data/subdir/scan2.dcm')]
    """
    pattern = f"*.{extension}" if extension else "*"

    glob_method = directory.rglob if recursive else directory.glob

    logger.debug(
        "Looking for DICOM files",
        directory=directory,
        recursive=recursive,
        search_pattern=pattern,
        check_header=check_header,
        limit=limit,
        search_input=search_input,
    )

    files = (
        file.absolute()
        for file in glob_method(pattern)
        if (
            not search_input  # no search input passed
            or all(term in str(file.as_posix()) for term in search_input)
        )
        and _is_valid_dicom(file, check_header)
    )

    return list(islice(files, limit)) if limit else list(files)
