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
    Sanitize the file name by removing potentially dangerous characters at the
    beginning and end of the filename, and replacing them elsewhere.

    Removes disallowed characters at the beginning and end of the filename,
    replaces disallowed characters with underscores, converts spaces to
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
    >>> sanitize_file_name("<bad>name.dcm")
    'bad_name.dcm'
    """
    assert filename is not None and filename != ""
    assert isinstance(filename, str)

    disallowed_characters_pattern = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

    # Remove disallowed characters at the beginning and end
    filename = re.sub(
        r'^[<>:"/\\|?*\x00-\x1f]+|[<>:"/\\|?*\x00-\x1f]+$', "", filename
    )

    # Remove spaces at the beginning and end
    filename = filename.strip()

    # Replace disallowed characters elsewhere with underscores
    sanitized_name = disallowed_characters_pattern.sub("_", filename)
    sanitized_name = sanitized_name.replace(" ", "_")
    sanitized_name = re.sub(r"(_{2,})", "_", sanitized_name)
    return sanitized_name
