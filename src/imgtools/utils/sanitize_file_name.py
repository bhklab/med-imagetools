"""
Functions
---------
sanitize_file_name(filename: str) -> str
    Sanitize filenames by replacing potentially dangerous characters.

Examples
--------
Sanitize a filename:
    >>> sanitize_file_name("test<>file:/name.dcm")
    'test_file_name.dcm'
"""

import re

# Disallowed characters (excluding `/`)
DISALLOWED_CHARS = r'<>:"\\|?*\x00-\x1f'
DISALLOWED_CHARS_PATTERN = re.compile(f"[{DISALLOWED_CHARS}]")
DISALLOWED_CHARS_STRIP_REGEX = re.compile(
    f"^[{DISALLOWED_CHARS}]+|[{DISALLOWED_CHARS}]+$"
)


def sanitize_file_name(filename: str) -> str:
    """
    Sanitize the file name by removing or replacing disallowed characters,
    while preserving forward slashes.

    Parameters
    ----------
    filename : str
        The input file name to sanitize.

    Returns
    -------
    str
        The sanitized file name.
    """
    assert filename and isinstance(filename, str)

    # Remove disallowed characters at the start and end
    filename = DISALLOWED_CHARS_STRIP_REGEX.sub("", filename).strip()

    filename = filename.replace(" - ", "-")

    # Replace multiple spaces with a single space
    filename = re.sub(r"\s+", "_", filename)

    # Replace multiple consecutive disallowed characters with a single underscore
    filename = re.sub(f"[{DISALLOWED_CHARS}]+", "_", filename)

    # Replace remaining disallowed characters with underscores
    sanitized = DISALLOWED_CHARS_PATTERN.sub("_", filename)

    return sanitized
