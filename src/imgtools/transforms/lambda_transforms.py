from typing import Any, Callable, Optional

import SimpleITK as sitk

from .base_transform import BaseTransform

__all__ = ["SimpleITKFilter", "ImageFunction"]


# Lambda transforms
class SimpleITKFilter(BaseTransform):
    """SimpleITKFilter operation class:
    A callable class that accepts an sitk.ImageFilter object to add a filter to an image.

    To instantiate:
        obj = SimpleITKFilter(sitk_filter, *execute_args)
    To call:
        result = obj(image)

    Parameters
    ----------
    sitk_filter
        An ImageFilter object in sitk library.

    execute_args, optional
        Any arguments to be passed to the Execute() function of the selected ImageFilter object.
    """

    def __init__(
        self,
        sitk_filter: sitk.ImageFilter,
        *execute_args: Optional[Any],  # noqa: ANN401
    ) -> None:
        self.sitk_filter = sitk_filter
        self.execute_args = execute_args

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """SimpleITKFilter callable object:
        A callable class that uses an sitk.ImageFilter object to add a filter to an image.

        Parameters
        ----------
        image
            sitk.Image object to be processed.

        Returns
        -------
        sitk.Image
            The processed image with a given filter.
        """
        return self.sitk_filter.Execute(image, *self.execute_args)  # type: ignore


class ImageFunction(BaseTransform):
    """ImageFunction operation class:
    A callable class that takens in a function to be used to process an image,
    and executes it.

    To instantiate:
        obj = ImageFunction(function, copy_geometry, **kwargs)
    To call:
        result = obj(image)

    Parameters
    ----------
    function
        A function to be used for image processing.
        This function needs to have the following signature:
        - function(image: sitk.Image, **args)
        - The first argument needs to be an sitkImage, followed by optional arguments.

    copy_geometry, optional
        An optional argument to specify whether information about the image should be copied to the
        resulting image. Set to be true as a default.

    kwargs, optional
        Any number of arguements used in the given function.
    """

    def __init__(
        self,
        function: Callable[..., sitk.Image],
        copy_geometry: bool = True,
        **kwargs: Optional[Any],  # noqa: ANN401
    ) -> None:
        self.function = function
        self.copy_geometry = copy_geometry
        self.kwargs = kwargs

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """ImageFunction callable object:
        Process an image based on a given function.

        Parameters
        ----------
        image
            sitk.Image object to be processed.

        Returns
        -------
        sitk.Image
            The image processed with the given function.
        """

        result = self.function(image, **self.kwargs)
        if self.copy_geometry:
            result.CopyInformation(image)
        return result
