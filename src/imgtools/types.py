"""
This module provides type definitions to ensure consistency and readability across the project.

Currently, it includes:
- `PathLike`: A type alias for file paths that supports both strings and objects from the
  `os` and `pathlib` modules.
"""

import os
from typing import Union

__all__ = ["PathLike"]

#: PathLike
#
# A type alias for file path representations.
#
# This type is useful for functions that accept file paths as arguments. It supports:
# - `str`: Standard string paths (e.g., "example/file.txt").
# - `os.PathLike`: Objects implementing the `__fspath__` protocol, such as `pathlib.Path`.
#
# Example usage:
# ```
# def process_file(path: PathLike) -> None:
#     with open(path, 'r') as f:
#         print(f.read())
# ```
PathLike = Union[str, os.PathLike]
