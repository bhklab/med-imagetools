class DirectoryNotFoundError(Exception):
    pass


####################################################################################################
# Dicom spcific exceptions


class InvalidDicomError(Exception):
    pass


class NotRTSTRUCTError(InvalidDicomError):
    """Exception raised when loading a non-RTSTRUCT DICOM file."""

    pass


class NotSEGError(InvalidDicomError):
    """Exception raised when loading a non-SEG DICOM file."""

    pass


class RTSTRUCTAttributeError(InvalidDicomError):
    """Exception raised for attribute errors in the RTSTRUCT DICOM file."""

    pass


class MissingROIError(KeyError):
    """Custom exception for missing ROI in the structure set."""

    pass


class ROIContourError(Exception):
    """Custom exception for missing ROI contour data in the RTSTRUCT file."""

    pass
