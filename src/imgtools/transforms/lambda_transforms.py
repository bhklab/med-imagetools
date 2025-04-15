from typing import Any, Callable

import SimpleITK as sitk

from .base_transform import BaseTransform

__all__ = ["SimpleITKFilter", "ImageFunction"]


# Lambda transforms
class SimpleITKFilter(BaseTransform):
    """SimpleITKFilter operation class.

    A callable class that accepts an sitk.ImageFilter object to add a filter
    to an image.

    To instantiate:
        obj = SimpleITKFilter(sitk_filter, *execute_args)
    To call:
        result = obj(image)

    Parameters
    ----------
    sitk_filter : sitk.ImageFilter
        An ImageFilter object in sitk library.
    execute_args : Optional[Any], optional
        Any arguments to be passed to the Execute() function of the selected
        ImageFilter object.
    """

    def __init__(
        self,
        sitk_filter: sitk.ImageFilter,
        *execute_args: Any | None,  # noqa: ANN401
    ) -> None:
        """Initialize a SimpleITKFilter with a filter and execution args.

        Parameters
        ----------
        sitk_filter : sitk.ImageFilter
            A SimpleITK image filter instance to process images.
        execute_args : Optional[Any], optional
            Optional positional arguments to pass to the filter's Execute
            method.
        """
        self.sitk_filter = sitk_filter
        self.execute_args = execute_args

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """Apply a SimpleITK image filter to an image.

        Executes the underlying filter with the provided image and any
        additional execution arguments.

        Parameters
        ----------
        image : sitk.Image
            The image to process.

        Returns
        -------
        sitk.Image
            The filtered image.
        """
        return self.sitk_filter.Execute(image, *self.execute_args)  # type: ignore


class ImageFunction(BaseTransform):
    """ImageFunction operation class.

    A callable class that takens in a function to be used to process an image,
    and executes it.

    To instantiate:
        obj = ImageFunction(function, copy_geometry, **kwargs)
    To call:
        result = obj(image)

    Parameters
    ----------
    function : Callable[..., sitk.Image]
        A function to be used for image processing.
        This function needs to have the following signature:
        - function(image: sitk.Image, **args)
        - The first argument needs to be an sitkImage, followed by optional
          arguments.
    copy_geometry : bool, optional
        An optional argument to specify whether information about the image
        should be copied to the resulting image. Set to be true as a default.
    kwargs : Optional[Any], optional
        Any number of arguments used in the given function.
    """

    def __init__(
        self,
        function: Callable[..., sitk.Image],
        copy_geometry: bool = True,
        **kwargs: Any | None,  # noqa: ANN401
    ) -> None:
        """Initialize an ImageFunction transform.

        Registers a user-defined function for image processing along with its
        settings. The supplied function must accept a SimpleITK image and
        return a processed image. If copy_geometry is True, the geometry of
        the input image will be copied to the output.

        Parameters
        ----------
        function : Callable[..., sitk.Image]
            A callable that processes a SimpleITK image and returns a
            processed image.
        copy_geometry : bool, optional
            If True, copies the input image's geometry to the result.
        kwargs : Optional[Any], optional
            Optional keyword arguments to be passed to the processing function.
        """
        self.function = function
        self.copy_geometry = copy_geometry
        self.kwargs = kwargs

    def __call__(self, image: sitk.Image) -> sitk.Image:
        """Process an image using a custom function.

        This method applies the user-defined function to the input image with
        any additional keyword arguments. If the `copy_geometry` flag is set,
        it copies the geometric information from the original image to the
        result.

        Parameters
        ----------
        image : sitk.Image
            The image to be processed.

        Returns
        -------
        sitk.Image
            The processed image.
        """

        result = self.function(image, **self.kwargs)
        if self.copy_geometry:
            result.CopyInformation(image)
        return result
