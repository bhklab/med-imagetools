class DirectoryNotFoundError(Exception):
    pass


class InvalidDicomError(Exception):
    pass


class NotRTSTRUCTError(InvalidDicomError):
    """Exception raised for errors in the RTSTRUCT DICOM file."""

    pass


class RTSTRUCTAttributeError(InvalidDicomError):
    """Exception raised for attribute errors in the RTSTRUCT DICOM file."""

    pass
