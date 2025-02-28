import importlib
from typing import Any, Tuple


class OptionalImportError(ImportError):
    def __init__(
        self,
        module_name: str,
        extra_name: str | None = None,
    ) -> None:
        if extra_name:
            msg = (
                f"Module '{module_name}' is required but not installed. "
                f"Install it via 'pip install med-imagetools[{extra_name}]'."
            )
        else:
            msg = (
                f"Module '{module_name}' is required but not installed. "
                f"Install it via 'pip install med-imagetools[{module_name}]'."
            )
        super().__init__(msg)


def optional_import(
    module_name: str,
    raise_error: bool = False,
) -> Tuple[Any, bool]:
    """
    Attempt to import an optional module and handle its absence gracefully.

    This function is useful when you want to provide optional features that depend
    on modules that may not be installed.

    Parameters
    ----------
    module_name : str
        Name of the module to import (e.g., 'numpy', 'torch').
    raise_error : bool, optional
        If True, raise an OptionalImportError when the module is not found.
        If False, return (None, False) when import fails.

    Returns
    -------
    tuple
        A tuple containing (module, success_flag), where:
        - module: The imported module if successful, None if failed
        - success_flag: True if import succeeded, False otherwise
    Examples
    --------
    >>> # Basic usage - silent failure
    >>> numpy, has_numpy = optional_import("numpy")
    >>> if not has_numpy:
    ...     raise OptionalImportError("numpy")

    >>> # Usage with error raising
    >>> torch, _ = optional_import(
    ...     "torch", raise_error=True
    ... )
    >>> # Will raise OptionalImportError if torch is not installed
    """
    try:
        module = importlib.import_module(module_name)
        return module, True
    except ImportError as ie:
        if raise_error:
            raise OptionalImportError(module_name) from ie
        return None, False
