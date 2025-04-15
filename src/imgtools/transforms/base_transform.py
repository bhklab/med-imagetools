from abc import ABC, abstractmethod
from typing import Any

from SimpleITK import Image


class BaseTransform(ABC):
    """Abstract base class for operations.

    Classes inheriting from this must implement the `__call__` method.
    """

    @property
    def name(self) -> str:
        """Return the name of the transform class for logging and debugging.

        Returns
        -------
        str
            The name of the transform class.
        """
        return self.__class__.__name__

    @abstractmethod
    def __call__(self, image: Image, *args: Any, **kwargs: Any) -> Image:  # noqa
        """
        Apply the transformation operation to the given image.

        This abstract method must be implemented by subclasses to apply a specific
        transformation. It takes an image along with optional positional and keyword
        arguments to customize the transformation and returns the resulting image.

        Parameters
        ----------
            image: The input image to be transformed.
            *args: Additional positional arguments for the transformation.
            **kwargs: Additional keyword arguments for the transformation.

        Returns
        -------
            The transformed image.
        """
        pass

    def __repr__(self) -> str:
        attrs = sorted(
            [(k, v) for k, v in self.__dict__.items() if not k.startswith("_")]
        )
        attrs = [(k, repr(v)) for k, v in attrs]
        args = ", ".join(f"{k}={v}" for k, v in attrs)
        return f"{self.__class__.__name__}({args})"

    def __str__(self) -> str:
        """Return a more user-friendly string representation.

        Returns
        -------
        str
            A human-readable description of the transform.
        """
        return self.name
