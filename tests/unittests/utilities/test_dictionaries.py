"""Unit tests for dict utilities with attribute and dot access."""

from datetime import datetime, timedelta
import math

import pytest

from imgtools.utils import dictionaries as dicts


def test_nested_attrdict_behavior():
	result = dicts.AttrDict.from_flat_dict({"user.name": "alice"})
	assert result == {"user": {"name": "alice"}}
	assert result.user.name == "alice"
	assert result["user"]["name"] == "alice"

	# Modify and flatten again
	result.user.name = "bob"
	assert result.to_flat_dict() == {"user.name": "bob"}


def test_missing_attr_raises_attributeerror():
	empty = dicts.attrify({})
	with pytest.raises(AttributeError):
		_ = empty.nonexistent


def test_recursive_attrify_conversion():
	structure = {"level": [{"deep": "value"}]}
	converted = dicts.attrify(structure)
	assert converted.level[0].deep == "value"


def test_dot_flattening_single_level():
	nested = {"config": {"timeout": 30}}
	flat = dicts.flatten_dictionary(nested)
	assert flat == {"config.timeout": 30}


def test_dot_inflation_simple_case():
	flat = {"settings.resolution": "1080p"}
	nested = dicts.expand_dictionary(flat)
	assert nested == {"settings": {"resolution": "1080p"}}


def test_get_field_missing_returns_none():
	assert dicts.retrieve_nested_value({}, "foo") is None
	assert dicts.retrieve_nested_value({}, "foo.bar") is None


def test_get_field_preserves_non_field_errors():
	class Broken:
		x = property(lambda self: self.missing())

	obj = {"outer": Broken()}

	with pytest.raises(AttributeError, match="object has no attribute 'missing'"):
		dicts.retrieve_nested_value(Broken(), "x")

	with pytest.raises(AttributeError, match="object has no attribute 'missing'"):
		dicts.retrieve_nested_value(obj, "outer.x")


def test_metadata_cleanup_converts_nan():
	payload = {
		"score": float("NaN"),
		"items": [2, float("NaN"), 4],
		"meta": {"threshold": float("NaN")}
	}

	# Ensure not already None
	assert math.isnan(payload["score"])

	cleaned = dicts.cleanse_metadata(payload)

	assert cleaned["score"] is None
	assert cleaned["items"][1] is None
	assert cleaned["meta"]["threshold"] is None


def test_metadata_cleanup_converts_datetime():
	now = datetime.now()
	timestamp = now + timedelta(days=1)

	data = {
		"start": timestamp,
		"events": ["boot", timestamp, "shutdown"],
		"log": {"created": timestamp}
	}

	expected = timestamp.isoformat(timespec="seconds")
	assert data["start"] != expected  # prove it's a datetime before cleanup

	converted = dicts.cleanse_metadata(data)

	assert converted["start"] == expected
	assert expected in converted["events"]
	assert converted["log"]["created"] == expected