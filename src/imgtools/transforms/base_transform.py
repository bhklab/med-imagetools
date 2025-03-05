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
        Apply the transformation operation to the given image.
        
        This abstract method must be implemented by subclasses to apply a specific
        transformation. It takes an image along with optional positional and keyword
        arguments to customize the transformation and returns the resulting image.
        
        Args:
            image: The input image to be transformed.
            *args: Additional positional arguments for the transformation.
            **kwargs: Additional keyword arguments for the transformation.
        
        Returns:
            The transformed image.
        """
        pass

    def __repr__(self) -> str:
        """
        Return a string representation of the transform instance.
        
        This method constructs a formatted string that includes the class name and all
        public attributes (i.e. those not starting with an underscore). The attributes
        are sorted alphabetically and displayed using their repr() values.
        
        Returns:
            str: A formatted string in the form "ClassName(attr1=repr(value1), ...)".
        """
        attrs = sorted(
            [(k, v) for k, v in self.__dict__.items() if not k.startswith("_")]
        )
        attrs = [(k, repr(v)) for k, v in attrs]
        args = ", ".join(f"{k}={v}" for k, v in attrs)
        return f"{self.__class__.__name__}({args})"
