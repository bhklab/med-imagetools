from abc import ABC, abstractmethod
from typing import Any
from SimpleITK import Image

class BaseTransform(ABC):
    """Abstract base class for operations.

    Classes inheriting from this must implement the `__call__` method.
    """

    @abstractmethod
    def __call__(self, image: Image, *args: Any, **kwargs: Any) -> Image:  # noqa
        """Perform the operation."""
        pass

    def __repr__(self) -> str:
        """
        Generate a string representation of the operation instance.

        Returns
        -------
        str
            The string representation of the object.
        """
        attrs = [
            (k, v) for k, v in self.__dict__.items() if not k.startswith("_")
        ]
        attrs = [
            (k, f"'{v}'") if isinstance(v, str) else (k, v) for k, v in attrs
        ]
        args = ", ".join(f"{k}={v}" for k, v in attrs)
        return f"{self.__class__.__name__}({args})"
