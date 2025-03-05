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
        """
        Initialize a SimpleITKFilter instance.
        
        Sets the SimpleITK image filter to be applied and any additional arguments for the filter's Execute method.
        
        Args:
            sitk_filter: A SimpleITK image filter used for processing images.
            *execute_args: Optional positional arguments for the filter's Execute method.
        """
        self.sitk_filter = sitk_filter
        self.execute_args = execute_args

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """Apply the SimpleITK filter to the input image.
        
        Processes the image using the associated SimpleITK filter with any additional execution arguments.
        
        Parameters:
            image: A SimpleITK image to be processed.
        
        Returns:
            The filtered SimpleITK image.
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
        """
        Initializes the ImageFunction transform with a custom image processing function.
        
        This transform applies a user-defined callable to an input image. The provided function is expected
        to accept an sitk.Image and return a processed sitk.Image. If copy_geometry is True, the geometric
        properties of the input image (e.g., origin, spacing, direction) are copied to the output.
        
        Parameters:
            function: A callable that processes an image and returns a transformed sitk.Image.
            copy_geometry: Boolean flag indicating whether to replicate the input image's geometry in the output.
            kwargs: Additional keyword arguments to pass to the processing function.
        """
        self.function = function
        self.copy_geometry = copy_geometry
        self.kwargs = kwargs

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """
        Applies the user-defined function to process an image.
        
        This method calls the provided function with the input image and any additional keyword
        arguments. If the copy_geometry flag is set, the spatial metadata of the input image is
        copied to the resulting image.
        
        Parameters:
            image (sitk.Image): The input image to process.
        
        Returns:
            sitk.Image: The processed image.
        """

        result = self.function(image, **self.kwargs)
        if self.copy_geometry:
            result.CopyInformation(image)
        return result
