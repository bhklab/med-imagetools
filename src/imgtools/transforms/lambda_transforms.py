from typing import Any, Callable

import SimpleITK as sitk

from .base_transform import BaseTransform

__all__ = ["SimpleITKFilter", "ImageFunction"]


# Lambda transforms
class SimpleITKFilter(BaseTransform):
    """Apply a SimpleITK image filter to an image.

    This class wraps a SimpleITK image filter and allows it to be used like any
    other transform in the library. It provides a consistent interface for
    applying SimpleITK filters within the transform framework.

    Parameters
    ----------
    sitk_filter : sitk.ImageFilter
        A SimpleITK image filter instance to process images.
    *execute_args : Any, optional
        Optional positional arguments to pass to the filter's Execute method.
        These arguments come after the input image in the Execute call.

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> from imgtools.datasets.sample_images import (
    ...     create_noisy_sphere_image,
    ... )
    >>> from imgtools.transforms import SimpleITKFilter
    >>> # Create a sample image with noise
    >>> image = create_noisy_sphere_image(
    ...     noise_level=0.3
    ... )
    >>> # Create a median filter to remove noise
    >>> median_filter = sitk.MedianImageFilter()
    >>> median_filter.SetRadius(2)
    >>> # Use SimpleITKFilter to apply the filter
    >>> median_transform = SimpleITKFilter(median_filter)
    >>> filtered_image = median_transform(image)
    >>> # Use SimpleITKFilter with a different filter that takes parameters
    >>> gradient_magnitude = sitk.GradientMagnitudeRecursiveGaussianImageFilter()
    >>> gradient_transform = SimpleITKFilter(
    ...     gradient_magnitude, 1.5
    ... )  # sigma=1.5
    >>> gradient_image = gradient_transform(image)
    >>> print(
    ...     "Applied median filter and gradient magnitude filter"
    ... )
    Applied median filter and gradient magnitude filter
    """

    def __init__(
        self,
        sitk_filter: sitk.ImageFilter,
        *execute_args: Any,  # noqa: ANN401
    ) -> None:
        """Initialize a SimpleITKFilter with a filter and execution args.

        Parameters
        ----------
        sitk_filter : sitk.ImageFilter
            A SimpleITK image filter instance to process images.
        *execute_args : Any, optional
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
    """Apply a custom function to process an image.

    This class wraps a user-defined function and allows it to be used like
    any other transform in the library. The function must accept a SimpleITK
    image as its first parameter and return a SimpleITK image.

    Parameters
    ----------
    function : Callable[..., sitk.Image]
        A callable that processes a SimpleITK image and returns a
        processed image.
    copy_geometry : bool, optional
        If True, copies the input image's geometry to the result.
    **kwargs : Any, optional
        Optional keyword arguments to be passed to the processing function.

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> import numpy as np
    >>> from imgtools.datasets.sample_images import (
    ...     create_sphere_image,
    ... )
    >>> from imgtools.transforms import ImageFunction
    >>> # Create a sample sphere image
    >>> image = create_sphere_image()
    >>> # Define a custom function to invert intensities
    >>> def invert_intensity(image, max_value=1.0):
    ...     return sitk.Subtract(max_value, image)
    >>> # Create a transform using this function
    >>> inverter = ImageFunction(
    ...     invert_intensity, max_value=1.0
    ... )
    >>> inverted = inverter(image)
    >>> # Define a function that operates on the NumPy array
    >>> def add_random_noise(image, noise_level=0.1):
    ...     array = sitk.GetArrayFromImage(image)
    ...     noise = np.random.normal(
    ...         0, noise_level, array.shape
    ...     )
    ...     array = array + noise
    ...     result = sitk.GetImageFromArray(array)
    ...     result.CopyInformation(image)
    ...     return result
    >>> # Create and apply a noise transform
    >>> noiser = ImageFunction(
    ...     add_random_noise, noise_level=0.2
    ... )
    >>> noisy = noiser(image)
    >>> print("Applied custom image transforms")
    Applied custom image transforms
    """

    def __init__(
        self,
        function: Callable[..., sitk.Image],
        copy_geometry: bool = True,
        **kwargs: Any,  # noqa: ANN401
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
        **kwargs : Any, optional
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
