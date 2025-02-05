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


def sanitize_file_name(filename: str) -> str:
    """
    Sanitize the file name by replacing potentially dangerous characters.

    Replaces disallowed characters with underscores, converts spaces to
    underscores, and removes subsequent underscores.

    Parameters
    ----------
    filename : str
        The input file name to sanitize.

    Returns
    -------
    str
        The sanitized file name.

    Examples
    --------
    >>> sanitize_file_name("test<>file:/name.dcm")
    'test_file_name.dcm'
    >>> sanitize_file_name("my file name.dcm")
    'my_file_name.dcm'
    """
    assert filename is not None
    assert isinstance(filename, str)

    disallowed_characters_pattern = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
    sanitized_name = disallowed_characters_pattern.sub("_", filename)
    sanitized_name = sanitized_name.replace(" ", "_")
    sanitized_name = re.sub(r"(_{2,})", "_", sanitized_name)
    return sanitized_name
