"""Dict utility functions and classes supporting attribute access and dot-notation.

This module provides tools for working with dictionaries that allow:
    - Attribute-style access to dictionary keys
    - Conversion between nested and flattened (dot-notated) dictionaries
    - Safe access to nested dictionary or object fields
    - Recursive data cleaning of metadata dictionaries

Examples
--------
>>> d = AttrDict({"a": {"b": 1}})
>>> d.a.b
1

>>> flatten_dictionary({"a": {"b": 1}})
{'a.b': 1}

>>> expand_dictionary({"a.b": 1})
{'a': {'b': 1}}
"""

from __future__ import annotations

import collections.abc
import datetime
from typing import Any
import math

from .date_time import datetime_to_iso_string

__all__ = [
    "AttrDict",
    "flatten_dictionary",
    "expand_dictionary",
    "retrieve_nested_value",
    "cleanse_metadata",
]


class AttrDict(dict):
    """A dictionary that supports dot-style attribute access and nested utilities.

    This class extends the built-in `dict` to enable accessing keys as attributes
    and includes helpers to flatten and expand nested structures.

    Examples
    --------
    >>> d = AttrDict({"x": {"y": 5}})
    >>> d.x.y
    5

    >>> flat = d.to_flat_dict()
    >>> flat
    {'x.y': 5}

    >>> AttrDict.from_flat_dict({"x.y": 5})
    {'x': {'y': 5}}
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # if empty, initialize with an empty dict
        if not args and not kwargs:
            super().__init__()
            return

        super().__init__(
            {k: attrify(v) for k, v in dict(*args, **kwargs).items()}
        )

    @classmethod
    def from_flat_dict(cls, *args: Any, **kwargs: Any) -> AttrDict:
        """Inflate a flat dict into a nested AttrDict.

        Example
        -------
        >>> AttrDict.from_flat_dict({"a.b": 1})
        {'a': {'b': 1}}
        """
        return cls(expand_dictionary(dict(*args, **kwargs)))

    def to_flat_dict(self) -> dict[str, Any]:
        """Return a flattened dictionary using dot-notation keys."""
        return flatten_dictionary(self)

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            msg = f"{self.__class__.__name__!r} has no attribute {name!r}"
            raise AttributeError(msg) from None

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value

    def __repr__(self) -> str:
        """Return a pretty representation of the AttrDict."""
        from pprint import pformat

        return f"{self.__class__.__name__}({pformat(dict(self))})"


def attrify(data: Any) -> Any:
    """Recursively convert dicts to AttrDict and handle lists of dicts as well."""
    if isinstance(data, dict):
        return AttrDict(data)
    if isinstance(data, list):
        return [attrify(elem) for elem in data]
    return data


def flatten_dictionary(
    nested_dict: dict[str, Any], parent_key_prefix: str = ""
) -> dict[str, Any]:
    """Flatten a nested dictionary using dot-notation keys.

    Parameters
    ----------
    nested_dict : dict
        The nested dictionary to flatten.
    parent_key_prefix : str, optional
        Prefix for internal recursive use.

    Returns
    -------
    dict
        Flattened dictionary.

    Examples
    --------
    >>> flatten_dictionary({"a": {"b": 1}})
    {'a.b': 1}
    """
    flat_dict: dict[str, Any] = {}
    for key, value in nested_dict.items():
        full_key = f"{parent_key_prefix}.{key}" if parent_key_prefix else key
        if isinstance(value, dict):
            flat_dict.update(
                flatten_dictionary(value, parent_key_prefix=full_key)
            )
        else:
            flat_dict[full_key] = value
    return flat_dict


def expand_dictionary(flat_dict: dict[str, Any]) -> dict[str, Any]:
    """Expand dot-notated keys into a nested dictionary.

    Parameters
    ----------
    flat_dict : dict
        Dictionary with keys in dot-notation.

    Returns
    -------
    dict
        Nested dictionary.

    Examples
    --------
    >>> expand_dictionary({"a.b": 1})
    {'a': {'b': 1}}
    """
    nested_dict: dict[str, Any] = {}
    for key, value in flat_dict.items():
        parts = key.split(".")
        node = nested_dict
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return nested_dict


def retrieve_nested_value(container: Any, field_path: str) -> Any | None:
    """Retrieve a value or attribute using a dot-notation path.

    Parameters
    ----------
    container : Any
        The object or dictionary to access.
    field_path : str
        Dot-notation string path.

    Returns
    -------
    Any or None
        The resolved value or None if not found.

    Examples
    --------
    >>> retrieve_nested_value({"a": {"b": 1}}, "a.b")
    1
    """
    try:
        return container[field_path]
    except (TypeError, KeyError):
        pass
    try:
        return getattr(container, field_path)
    except AttributeError as exc:
        if f"object has no attribute {field_path!r}" not in str(exc):
            raise

    node = container
    for part in field_path.split("."):
        try:
            node = node[part]
            continue
        except (TypeError, KeyError):
            pass
        try:
            node = getattr(node, part)
            continue
        except AttributeError as exc:
            if f"object has no attribute {part!r}" not in str(exc):
                raise
            return None
    return node


def cleanse_metadata(metadata: Any) -> Any:
    """Recursively cleanse metadata dictionaries for serialization.

    Fixes applied:
        1. Converts NaN values to None.
        2. Cleans nested dictionaries and iterables.
        3. Converts datetime.{datetime,date,time} to ISO format strings.

    Parameters
    ----------
    metadata : Any
        The input dictionary, list, or primitive.

    Returns
    -------
    Any
        The cleansed version of the input.
    """

    match metadata:
        case dict():
            return {k: cleanse_metadata(v) for k, v in metadata.items()}
        case collections.abc.Iterable() if not isinstance(
            metadata, (str, bytes)
        ):
            return [cleanse_metadata(v) for v in metadata]
        case float() if math.isnan(metadata):
            return None
        case datetime.datetime() | datetime.date() | datetime.time():
            return datetime_to_iso_string(metadata)
        case _:
            return metadata

    return metadata


# disable ruff
# ruff: noqa
if __name__ == "__main__":  # pragma: no cover
    # an example to show how to use the module
    from rich.pretty import pprint
    # Example usage

    nested_dict = {
        "a": {
            "b": 1,
            "c": {
                "d": 2,
                "e": [3, 4],
            },
        },
        "f": 5,
        "g": datetime.datetime.now(),
        "h": datetime.date(2024, 1, 1),
        "i_lists": [
            {"j": 6},
            {"j": 7},
            {"j": 8},
            {"j": 9},
        ],
    }
    print("Original Nested Dictionary:")
    pprint(nested_dict)

    flat_dict = flatten_dictionary(nested_dict)
    print("Flattened Dictionary:")
    pprint(flat_dict)

    expanded_dict = expand_dictionary(flat_dict)
    print("\nExpanded Dictionary:")
    pprint(expanded_dict)

    attr_dict = AttrDict(nested_dict)
    print("\nAttrDict:")
    pprint(attr_dict)

    print("\nAccessing nested value:")
    print(attr_dict.a.b)
    print(attr_dict.a.c.d)
