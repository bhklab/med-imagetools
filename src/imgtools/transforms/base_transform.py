from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from SimpleITK import Image

# Define a TypeVar for images that includes SimpleITK.Image and any subclasses
T_Image = TypeVar("T_Image", bound=Image)


class BaseTransform(Generic[T_Image], ABC):
    """Abstract base class for image transforms.

    Classes inheriting from this must implement the `__call__` method that
    applies a transformation to an image and returns the result.

    This class provides a common interface for all transforms in the package,
    allowing them to be used interchangeably and composed together.

    Type Parameters
    --------------
    T_Image
        The type of image this transform operates on. Defaults to SimpleITK.Image,
        but can be specialized to any subclass like MedImage or its derivatives.
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
    def __call__(self, image: T_Image, *args: Any, **kwargs: Any) -> T_Image:  # noqa
        """Apply the transformation operation to the given image.

        This abstract method must be implemented by subclasses to apply a specific
        transformation. It takes an image along with optional positional and keyword
        arguments to customize the transformation and returns the resulting image.

        Parameters
        ----------
        image : T_Image
            The input image to be transformed.
        *args : Any
            Additional positional arguments for the transformation.
        **kwargs : Any
            Additional keyword arguments for the transformation.

        Returns
        -------
        T_Image
            The transformed image, preserving the input type.
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
