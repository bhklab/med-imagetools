class DICOMSortError(Exception):
	"""Base exception for DICOM sorting errors."""

	pass


class InvalidPatternError(DICOMSortError):
	"""Raised when the target pattern is invalid."""

	pass


class InvalidDICOMKeyError(DICOMSortError):
	"""Raised when a DICOM key is invalid."""

	pass


class SorterBaseError(Exception):
	"""Base exception for sorting errors."""

	pass
