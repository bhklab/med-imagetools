from abc import ABC, abstractmethod
from typing import Any

from SimpleITK import Image


class BaseTransform(ABC):
    """Abstract base class for operations.

    Classes inheriting from this must implement the `__call__` method.
    """

    @abstractmethod
    def __call__(self, image: Image, *args: Any, **kwargs: Any) -> Image:  # noqa
        """
        Perform the transformation on the provided image.
        
        This abstract method should be overridden by subclasses to apply a specific image
        transformation. Additional positional and keyword arguments may be used to customize
        the operation.
        
        Args:
            image: The image to transform.
            *args: Optional positional arguments for transformation parameters.
            **kwargs: Optional keyword arguments for transformation settings.
        
        Returns:
            The transformed image.
        """
        pass

    def __repr__(self) -> str:
        """
        Return a string representation of the instance.
        
        The representation includes the class name and all public attributes (those not starting with an underscore),
        with each attribute's value shown using its repr. The attributes are sorted alphabetically to aid in debugging.
        """
        attrs = sorted(
            [(k, v) for k, v in self.__dict__.items() if not k.startswith("_")]
        )
        attrs = [(k, repr(v)) for k, v in attrs]
        args = ", ".join(f"{k}={v}" for k, v in attrs)
        return f"{self.__class__.__name__}({args})"
