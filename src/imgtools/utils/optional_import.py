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
    Attempt to import a module, returning (module, success).

    Parameters
    ----------
    module_name : str
      Name of the module to import.
    raise_error : bool, optional
      If True, raise an OptionalImportError when the module is not found. Otherwise, return (None, False).

    Returns
    -------
    tuple
      (imported module or None, True if import succeeded, False otherwise)
    """
    try:
        module = importlib.import_module(module_name)
        return module, True
    except ImportError as ie:
        if raise_error:
            raise OptionalImportError(module_name) from ie
        return None, False
