# test_optional_import.py

import types
import pytest

from imgtools.utils import optional_import, OptionalImportError


def test_optional_import_success():
	# Test importing a known installed module
	math_module, success = optional_import("math")
	assert success is True
	assert isinstance(math_module, types.ModuleType)
	assert hasattr(math_module, "sqrt")


def test_optional_import_failure_no_raise():
	# Test importing a definitely missing module with no error raised
	mod, success = optional_import("definitely_missing_module_12345")
	assert mod is None
	assert success is False


def test_optional_import_failure_with_raise():
	# Test importing a missing module with raise_error=True
	with pytest.raises(OptionalImportError) as exc_info:
		optional_import("definitely_missing_module_12345", raise_error=True)

	msg = str(exc_info.value)
	assert "definitely_missing_module_12345" in msg
	assert "pip install med-imagetools[definitely_missing_module_12345]" in msg


def test_optional_importerror_with_extra_name():
	# Test OptionalImportError message with extra_name
	err = OptionalImportError("some_mod", extra_name="extra")
	assert "pip install med-imagetools[extra]" in str(err)