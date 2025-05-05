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
