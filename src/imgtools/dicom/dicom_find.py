from itertools import islice
import os
from pathlib import Path
from typing import Generator, List

from pydicom.misc import is_dicom

from imgtools.loggers import logger


def _is_valid_dicom(file: Path, check_header: bool) -> bool:
    """
    Notes
    -----
    Validation includes:
    - Ensuring the file exists and is not a directory.
    - Ensuring the file is a valid DICOM file if `check_header` is True.
    """
    if not file.is_file():
        return False
    if check_header:
        return is_dicom(file)
    return True


def _normalize_extension(extension: str) -> str:
    """Normalize extension by removing a leading dot, if present."""
    if not extension:
        return ""
    return extension[1:] if extension.startswith(".") else extension


def _matches_extension(file: Path, extension: str, case_sensitive: bool) -> bool:
    """Check whether a file matches the requested extension."""
    if not extension:
        return True

    file_ext = file.suffix[1:] if file.suffix.startswith(".") else file.suffix

    if case_sensitive:
        return file_ext == extension
    return file_ext.lower() == extension.lower()


def _matches_search_input(file: Path, search_input: List[str] | None) -> bool:
    """Check whether all search terms occur in the file path."""
    if not search_input:
        return True

    path_str = file.as_posix()
    return all(term in path_str for term in search_input)


def _iter_files_following_symlinks(
    directory: Path,
    recursive: bool,
) -> Generator[Path, None, None]:
    """
    Yield files from `directory`, following nested symlinked directories.

    This function also protects against symlink cycles by tracking the
    resolved real paths of visited directories.
    """
    if not directory.exists():
        logger.warning("Directory does not exist", directory=directory)
        return

    if not directory.is_dir():
        logger.warning("Path is not a directory", directory=directory)
        return

    if not recursive:
        for child in directory.iterdir():
            if child.is_file():
                yield child
        return

    seen_dirs: set[Path] = set()

    for root, dirnames, filenames in os.walk(directory, followlinks=True):
        root_path = Path(root)

        try:
            real_root = root_path.resolve()
        except OSError:
            logger.warning("Failed to resolve directory", directory=root_path)
            dirnames[:] = []
            continue

        if real_root in seen_dirs:
            dirnames[:] = []
            continue

        seen_dirs.add(real_root)

        # Prune child directories that would create loops.
        pruned_dirnames: list[str] = []
        for dirname in dirnames:
            child_dir = root_path / dirname
            try:
                real_child = child_dir.resolve()
            except OSError:
                logger.warning("Failed to resolve child directory", directory=child_dir)
                continue

            if real_child not in seen_dirs:
                pruned_dirnames.append(dirname)

        dirnames[:] = pruned_dirnames

        for filename in filenames:
            yield root_path / filename


def find_dicoms(
    directory: Path,
    recursive: bool = True,
    check_header: bool = False,
    extension: str = "dcm",
    case_sensitive: bool = False,
    limit: int | None = None,
    search_input: List[str] | None = None,
) -> List[Path]:
    """Locate DICOM files in a specified directory.

    This function scans a directory for files matching the specified extension
    and validates them as DICOM files based on the provided options. It supports
    recursive search, nested symbolic links to directories, and optional header
    validation to confirm file validity.

    Parameters
    ----------
    directory : Path
        The directory in which to search for DICOM files.
    recursive : bool
        Whether to include subdirectories in the search.
    check_header : bool
        Whether to validate files by checking for a valid DICOM header.
            - If `True`, perform DICOM header validation (slower but more accurate).
            - If `False`, skip header validation and rely on extension and file checks.
    extension : str, default="dcm"
        File extension to search for (e.g., "dcm"). If empty, consider all files
        regardless of extension.
    case_sensitive : bool, default=False
        Whether to perform a case-sensitive search for the file extension.
    limit : int, optional
        Maximum number of DICOM files to return. If `None`, return all found files.
    search_input : List[str], optional
        List of terms to filter files by. Only files containing all terms
        in their paths will be included. If `None`, no filtering is applied.

    Returns
    -------
    List[Path]
        A list of valid DICOM file paths found in the directory.
    """
    files = filter_valid_dicoms(
        directory=directory,
        check_header=check_header,
        case_sensitive=case_sensitive,
        search_input=search_input,
        extension=extension or "",
        recursive=recursive,
    )

    return list(islice(files, limit)) if limit else list(files)


def filter_valid_dicoms(
    directory: Path,
    check_header: bool,
    case_sensitive: bool,
    search_input: List[str] | None,
    extension: str,
    recursive: bool,
) -> Generator[Path, None, None]:
    """
    Yield valid DICOM file paths from a directory.

    Unlike the original glob/rglob implementation, this traversal follows
    nested symlinked directories.
    """
    normalized_extension = _normalize_extension(extension)

    logger.debug(
        "Searching for DICOM files",
        directory=directory,
        recursive=recursive,
        follow_symlinks=True,
        check_header=check_header,
        case_sensitive=case_sensitive,
        search_input=search_input,
        extension=normalized_extension,
    )

    for file in _iter_files_following_symlinks(directory, recursive):
        if not _matches_extension(file, normalized_extension, case_sensitive):
            continue

        if not _matches_search_input(file, search_input):
            continue

        if _is_valid_dicom(file, check_header):
            yield file.absolute()


def convert_to_case_insensitive(extension: str) -> str:
    """Deprecated helper kept for compatibility."""
    if not extension:
        return ""

    lower_extension = extension.lower()
    return "".join(f"[{char.lower()}{char.upper()}]" for char in lower_extension)