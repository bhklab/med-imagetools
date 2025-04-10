class DirectoryNotFoundError(Exception):
    pass


####################################################################################################
# Dicom spcific exceptions


class InvalidDicomError(Exception):
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


class ContourPointsAcrossSlicesError(Exception):
    """Exception raised when contour points span across multiple slices."""

    def __init__(
        self,
        roi_name: str,
        contour_num: int,
        slice_points_shape: tuple,
        z_values: list,
    ) -> None:
        self.roi_name = roi_name
        self.contour_num = contour_num
        self.slice_points_shape = slice_points_shape
        self.z_values = z_values
        super().__init__(self._generate_message())

    def _generate_message(self) -> str:
        return (
            f"Contour points for ROI '{self.roi_name}' and contour {self.contour_num} "
            f"(shape: {self.slice_points_shape}) span across multiple slices: {self.z_values}."
        )
