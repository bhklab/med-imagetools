"""Utility functions to create sample images for examples and tests.

This module provides functions that generate synthetic images for use in
documentation examples, tests, and demonstrations of image processing operations.
Each function creates a specific type of image with well-defined characteristics,
making them ideal for demonstrating transform behavior.
"""

import math
from typing import Optional, Tuple

import numpy as np
import SimpleITK as sitk

__all__ = [
    "create_sphere_image",
    "create_grid_image",
    "create_gradient_image",
    "create_cross_image",
    "create_rod_image",
    "create_noisy_sphere_image",
    "create_checkerboard_image",
    "create_ct_hounsfield_image",
]


def create_sphere_image(
    size: Tuple[int, int, int] = (64, 64, 64),
    spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    center: Optional[Tuple[float, float, float]] = None,
    radius: float = 20.0,
    pixel_type: int = sitk.sitkFloat32,
    background_value: float = 0.0,
    foreground_value: float = 1.0,
    origin: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> sitk.Image:
    """Create a 3D image containing a sphere.

    Parameters
    ----------
    size : Tuple[int, int, int], optional
        Image dimensions in pixels, by default (64, 64, 64)
    spacing : Tuple[float, float, float], optional
        Pixel spacing in physical units, by default (1.0, 1.0, 1.0)
    center : Optional[Tuple[float, float, float]], optional
        Center of the sphere in image coordinates. If None,
        defaults to the center of the image.
    radius : float, optional
        Radius of the sphere in physical units, by default 20.0
    pixel_type : int, optional
        SimpleITK pixel type, by default sitk.sitkFloat32
    background_value : float, optional
        Value for pixels outside the sphere, by default 0.0
    foreground_value : float, optional
        Value for pixels inside the sphere, by default 1.0
    origin : Tuple[float, float, float], optional
        Image origin in physical coordinates, by default (0.0, 0.0, 0.0)

    Returns
    -------
    sitk.Image
        A SimpleITK image containing a sphere

    Notes
    -----
    The sphere's appearance depends on the image spacing. The radius is specified
    in physical units, so changing the spacing will change how many pixels are
    included in the sphere.

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> from imgtools.datasets.sample_images import (
    ...     create_sphere_image,
    ... )
    >>> # Create a basic sphere image
    >>> image = create_sphere_image()
    >>> print(f"Image size: {image.GetSize()}")
    Image size: (64, 64, 64)
    >>> # Create a sphere with different pixel type and higher resolution
    >>> high_res = create_sphere_image(
    ...     size=(100, 100, 100), spacing=(0.5, 0.5, 0.5)
    ... )
    >>> print(f"High-res size: {high_res.GetSize()}")
    High-res size: (100, 100, 100)
    """
    # Create blank image
    image = sitk.Image(size, pixel_type)
    image.SetSpacing(spacing)
    image.SetOrigin(origin)

    # Get numpy array view for fast processing
    arr = sitk.GetArrayFromImage(image)

    # Determine image center if not provided
    if center is None:
        center = (size[0] // 2, size[1] // 2, size[2] // 2)

    # Fill sphere
    for z in range(size[2]):
        for y in range(size[1]):
            for x in range(size[0]):
                # Calculate distance from center in physical units
                dx = (x - center[0]) * spacing[0]
                dy = (y - center[1]) * spacing[1]
                dz = (z - center[2]) * spacing[2]
                distance = np.sqrt(dx**2 + dy**2 + dz**2)

                # Set value based on distance from center
                if distance <= radius:
                    arr[z, y, x] = foreground_value
                else:
                    arr[z, y, x] = background_value

    # Convert back to SimpleITK (note: array indexing is [z,y,x])
    result = sitk.GetImageFromArray(arr)
    result.SetSpacing(spacing)
    result.SetOrigin(origin)
    return result


def create_grid_image(
    size: Tuple[int, int, int] = (64, 64, 64),
    spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    grid_spacing: int = 8,
    pixel_type: int = sitk.sitkFloat32,
    background_value: float = 0.0,
    foreground_value: float = 1.0,
    origin: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> sitk.Image:
    """Create a 3D image with a grid pattern.

    Parameters
    ----------
    size : Tuple[int, int, int], optional
        Image dimensions in pixels, by default (64, 64, 64)
    spacing : Tuple[float, float, float], optional
        Pixel spacing in physical units, by default (1.0, 1.0, 1.0)
    grid_spacing : int, optional
        Spacing between grid lines in pixels, by default 8
    pixel_type : int, optional
        SimpleITK pixel type, by default sitk.sitkFloat32
    background_value : float, optional
        Value for pixels between grid lines, by default 0.0
    foreground_value : float, optional
        Value for pixels on grid lines, by default 1.0
    origin : Tuple[float, float, float], optional
        Image origin in physical coordinates, by default (0.0, 0.0, 0.0)

    Returns
    -------
    sitk.Image
        A SimpleITK image with a 3D grid pattern

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> from imgtools.datasets.sample_images import (
    ...     create_grid_image,
    ... )
    >>> # Create a grid image with default parameters
    >>> image = create_grid_image()
    >>> print(f"Image size: {image.GetSize()}")
    Image size: (64, 64, 64)
    >>> # Create a grid with denser lines
    >>> dense_grid = create_grid_image(grid_spacing=4)
    >>> print(
    ...     f"Created grid image with line spacing of {4} pixels"
    ... )
    Created grid image with line spacing of 4 pixels
    """
    # Create blank image
    image = sitk.Image(size, pixel_type)
    image.SetSpacing(spacing)
    image.SetOrigin(origin)

    # Fill with grid pattern
    for z in range(size[2]):
        for y in range(size[1]):
            for x in range(size[0]):
                if (
                    x % grid_spacing == 0
                    or y % grid_spacing == 0
                    or z % grid_spacing == 0
                ):
                    image[x, y, z] = foreground_value
                else:
                    image[x, y, z] = background_value

    return image


def create_gradient_image(
    size: Tuple[int, int, int] = (64, 64, 64),
    spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    direction: str = "x",
    min_value: float = 0.0,
    max_value: float = 1.0,
    pixel_type: int = sitk.sitkFloat32,
    origin: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> sitk.Image:
    """Create a 3D image with a gradient along a specified axis.

    Parameters
    ----------
    size : Tuple[int, int, int], optional
        Image dimensions in pixels, by default (64, 64, 64)
    spacing : Tuple[float, float, float], optional
        Pixel spacing in physical units, by default (1.0, 1.0, 1.0)
    direction : str, optional
        Direction of the gradient ('x', 'y', 'z', 'radial'), by default "x"
    min_value : float, optional
        Minimum value of the gradient, by default 0.0
    max_value : float, optional
        Maximum value of the gradient, by default 1.0
    pixel_type : int, optional
        SimpleITK pixel type, by default sitk.sitkFloat32
    origin : Tuple[float, float, float], optional
        Image origin in physical coordinates, by default (0.0, 0.0, 0.0)

    Returns
    -------
    sitk.Image
        A SimpleITK image with a gradient pattern

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> from imgtools.datasets.sample_images import (
    ...     create_gradient_image,
    ... )
    >>> # Create an X-axis gradient
    >>> x_gradient = create_gradient_image(
    ...     direction="x", min_value=-100, max_value=400
    ... )
    >>> print(
    ...     f"X-gradient value at start: {x_gradient[0, 32, 32]}"
    ... )
    X-gradient value at start: -100.0
    >>> print(
    ...     f"X-gradient value at end: {x_gradient[63, 32, 32]}"
    ... )
    X-gradient value at end: 400.0
    >>> # Create a radial gradient
    >>> radial = create_gradient_image(
    ...     direction="radial"
    ... )
    >>> print(f"Created radial gradient image")
    Created radial gradient image
    """
    # Create blank image
    image = sitk.Image(size, pixel_type)
    image.SetSpacing(spacing)
    image.SetOrigin(origin)

    center = [s // 2 for s in size]
    max_distance = np.sqrt(sum((s // 2) ** 2 for s in size))

    # Fill with gradient pattern
    for z in range(size[2]):
        for y in range(size[1]):
            for x in range(size[0]):
                if direction.lower() == "x":
                    value = min_value + (max_value - min_value) * (
                        x / (size[0] - 1)
                    )
                elif direction.lower() == "y":
                    value = min_value + (max_value - min_value) * (
                        y / (size[1] - 1)
                    )
                elif direction.lower() == "z":
                    value = min_value + (max_value - min_value) * (
                        z / (size[2] - 1)
                    )
                elif direction.lower() == "radial":
                    dx = x - center[0]
                    dy = y - center[1]
                    dz = z - center[2]
                    distance = np.sqrt(dx**2 + dy**2 + dz**2)
                    value = min_value + (max_value - min_value) * (
                        distance / max_distance
                    )
                else:
                    msg = f"Unknown gradient direction: {direction}"
                    raise ValueError(msg)

                image[x, y, z] = value

    return image


def create_cross_image(
    size: Tuple[int, int, int] = (64, 64, 64),
    spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    center: Optional[Tuple[int, int, int]] = None,
    thickness: int = 1,
    pixel_type: int = sitk.sitkFloat32,
    background_value: float = 0.0,
    foreground_value: float = 1.0,
    origin: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> sitk.Image:
    """Create a 3D image with a cross pattern centered at a specified point.

    Parameters
    ----------
    size : Tuple[int, int, int], optional
        Image dimensions in pixels, by default (64, 64, 64)
    spacing : Tuple[float, float, float], optional
        Pixel spacing in physical units, by default (1.0, 1.0, 1.0)
    center : Optional[Tuple[int, int, int]], optional
        Center of the cross in image coordinates. If None,
        defaults to the center of the image.
    thickness : int, optional
        Thickness of the cross lines in pixels, by default 1
    pixel_type : int, optional
        SimpleITK pixel type, by default sitk.sitkFloat32
    background_value : float, optional
        Value for pixels outside the cross, by default 0.0
    foreground_value : float, optional
        Value for pixels on the cross, by default 1.0
    origin : Tuple[float, float, float], optional
        Image origin in physical coordinates, by default (0.0, 0.0, 0.0)

    Returns
    -------
    sitk.Image
        A SimpleITK image with a 3D cross pattern

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> from imgtools.datasets.sample_images import (
    ...     create_cross_image,
    ... )
    >>> # Create a cross image with default parameters
    >>> image = create_cross_image()
    >>> print(f"Image size: {image.GetSize()}")
    Image size: (64, 64, 64)
    >>> # Create a cross with thicker lines
    >>> thick_cross = create_cross_image(thickness=3)
    >>> print(
    ...     f"Created cross image with line thickness of {3} pixels"
    ... )
    Created cross image with line thickness of 3 pixels
    """
    # Create blank image
    image = sitk.Image(size, pixel_type)
    image.SetSpacing(spacing)
    image.SetOrigin(origin)

    # Determine center if not provided
    if center is None:
        center = (size[0] // 2, size[1] // 2, size[2] // 2)

    # Fill with background
    for z in range(size[2]):
        for y in range(size[1]):
            for x in range(size[0]):
                # Check if point is on any of the three axes of the cross
                half_thickness = thickness // 2
                on_x_axis = (
                    abs(y - center[1]) <= half_thickness
                    and abs(z - center[2]) <= half_thickness
                )
                on_y_axis = (
                    abs(x - center[0]) <= half_thickness
                    and abs(z - center[2]) <= half_thickness
                )
                on_z_axis = (
                    abs(x - center[0]) <= half_thickness
                    and abs(y - center[1]) <= half_thickness
                )

                if on_x_axis or on_y_axis or on_z_axis:
                    image[x, y, z] = foreground_value
                else:
                    image[x, y, z] = background_value

    return image


def create_rod_image(
    size: Tuple[int, int, int] = (64, 64, 64),
    spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    axis: str = "x",
    radius: int = 1,
    pixel_type: int = sitk.sitkFloat32,
    background_value: float = 0.0,
    foreground_value: float = 1.0,
    origin: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> sitk.Image:
    """Create a 3D image with a rod along a specified axis.

    Parameters
    ----------
    size : Tuple[int, int, int], optional
        Image dimensions in pixels, by default (64, 64, 64)
    spacing : Tuple[float, float, float], optional
        Pixel spacing in physical units, by default (1.0, 1.0, 1.0)
    axis : str, optional
        The axis along which the rod extends ('x', 'y', or 'z'), by default "x"
    radius : int, optional
        Radius of the rod in pixels, by default 1
    pixel_type : int, optional
        SimpleITK pixel type, by default sitk.sitkFloat32
    background_value : float, optional
        Value for pixels outside the rod, by default 0.0
    foreground_value : float, optional
        Value for pixels inside the rod, by default 1.0
    origin : Tuple[float, float, float], optional
        Image origin in physical coordinates, by default (0.0, 0.0, 0.0)

    Returns
    -------
    sitk.Image
        A SimpleITK image containing a rod

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> from imgtools.datasets.sample_images import (
    ...     create_rod_image,
    ... )
    >>> # Create a rod along the x-axis
    >>> x_rod = create_rod_image(axis="x")
    >>> print(f"Created rod along x-axis")
    Created rod along x-axis
    >>> # Create a thicker rod along the z-axis
    >>> z_rod = create_rod_image(axis="z", radius=2)
    >>> print(
    ...     f"Created rod along z-axis with radius {2}"
    ... )
    Created rod along z-axis with radius 2
    """
    # Create blank image
    image = sitk.Image(size, pixel_type)
    image.SetSpacing(spacing)
    image.SetOrigin(origin)

    center_x = size[0] // 2
    center_y = size[1] // 2
    center_z = size[2] // 2

    # Fill with rod
    for z in range(size[2]):
        for y in range(size[1]):
            for x in range(size[0]):
                # Calculate distance from axis
                if axis.lower() == "x":
                    distance = math.sqrt(
                        (y - center_y) ** 2 + (z - center_z) ** 2
                    )
                elif axis.lower() == "y":
                    distance = math.sqrt(
                        (x - center_x) ** 2 + (z - center_z) ** 2
                    )
                elif axis.lower() == "z":
                    distance = math.sqrt(
                        (x - center_x) ** 2 + (y - center_y) ** 2
                    )
                else:
                    msg = f"Unknown axis: {axis}"
                    raise ValueError(msg)

                if distance <= radius:
                    image[x, y, z] = foreground_value
                else:
                    image[x, y, z] = background_value

    return image


def create_noisy_sphere_image(
    size: Tuple[int, int, int] = (64, 64, 64),
    spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    center: Optional[Tuple[int, int, int]] = None,
    radius: float = 20.0,
    noise_level: float = 0.2,
    pixel_type: int = sitk.sitkFloat32,
    background_value: float = 0.0,
    foreground_value: float = 1.0,
    origin: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> sitk.Image:
    """Create a 3D image containing a sphere with noise.

    Parameters
    ----------
    size : Tuple[int, int, int], optional
        Image dimensions in pixels, by default (64, 64, 64)
    spacing : Tuple[float, float, float], optional
        Pixel spacing in physical units, by default (1.0, 1.0, 1.0)
    center : Tuple[int, int, int], optional
        Center of the sphere in image coordinates. If None,
        defaults to the center of the image.
    radius : float, optional
        Radius of the sphere in physical units, by default 20.0
    noise_level : float, optional
        Standard deviation of Gaussian noise to add, by default 0.2
    pixel_type : int, optional
        SimpleITK pixel type, by default sitk.sitkFloat32
    background_value : float, optional
        Value for pixels outside the sphere, by default 0.0
    foreground_value : float, optional
        Value for pixels inside the sphere, by default 1.0
    origin : Tuple[float, float, float], optional
        Image origin in physical coordinates, by default (0.0, 0.0, 0.0)

    Returns
    -------
    sitk.Image
        A SimpleITK image containing a noisy sphere

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> from imgtools.datasets.sample_images import (
    ...     create_noisy_sphere_image,
    ... )
    >>> # Create a basic noisy sphere image
    >>> noisy_image = create_noisy_sphere_image()
    >>> print(f"Created noisy sphere image")
    Created noisy sphere image
    >>> # Create a sphere with higher noise level
    >>> very_noisy = create_noisy_sphere_image(
    ...     noise_level=0.5
    ... )
    >>> print(f"Created sphere with noise level: {0.5}")
    Created sphere with noise level: 0.5
    """
    # Create sphere first
    image = create_sphere_image(
        size=size,
        spacing=spacing,
        center=center,
        radius=radius,
        pixel_type=pixel_type,
        background_value=background_value,
        foreground_value=foreground_value,
        origin=origin,
    )

    # Add noise
    if noise_level > 0:
        noise = sitk.Image(size, pixel_type)
        arr = sitk.GetArrayFromImage(noise)
        arr = np.random.normal(0, noise_level, arr.shape)
        noise = sitk.GetImageFromArray(arr)
        noise.CopyInformation(image)

        # Ensure noise has the same pixel type as the image
        noise = sitk.Cast(noise, image.GetPixelID())

        # Only add noise to the foreground
        mask = (
            sitk.Equal(image, foreground_value)
            if background_value != foreground_value
            else sitk.Image(image.GetSize(), sitk.sitkUInt8) + 1
        )
        mask = sitk.Cast(mask, image.GetPixelID())
        noisy_image = sitk.Add(image, sitk.Multiply(noise, mask))
        noisy_image.CopyInformation(image)
        return noisy_image
    else:
        return image


def create_checkerboard_image(
    size: Tuple[int, int, int] = (64, 64, 64),
    spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    checker_size: int = 8,
    pixel_type: int = sitk.sitkFloat32,
    value1: float = 0.0,
    value2: float = 1.0,
    origin: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> sitk.Image:
    """Create a 3D image with a checkerboard pattern.

    Parameters
    ----------
    size : Tuple[int, int, int], optional
        Image dimensions in pixels, by default (64, 64, 64)
    spacing : Tuple[float, float, float], optional
        Pixel spacing in physical units, by default (1.0, 1.0, 1.0)
    checker_size : int, optional
        Size of each checker cube in pixels, by default 8
    pixel_type : int, optional
        SimpleITK pixel type, by default sitk.sitkFloat32
    value1 : float, optional
        First alternating value, by default 0.0
    value2 : float, optional
        Second alternating value, by default 1.0
    origin : Tuple[float, float, float], optional
        Image origin in physical coordinates, by default (0.0, 0.0, 0.0)

    Returns
    -------
    sitk.Image
        A SimpleITK image with a 3D checkerboard pattern

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> from imgtools.datasets.sample_images import (
    ...     create_checkerboard_image,
    ... )
    >>> # Create a checkerboard image with default parameters
    >>> image = create_checkerboard_image()
    >>> print(f"Created checkerboard image")
    Created checkerboard image
    >>> # Create a checkerboard with smaller checker size
    >>> fine_checker = create_checkerboard_image(
    ...     checker_size=4
    ... )
    >>> print(
    ...     f"Created checkerboard with cube size: {4}"
    ... )
    Created checkerboard with cube size: 4
    """
    # Create blank image
    image = sitk.Image(size, pixel_type)
    image.SetSpacing(spacing)
    image.SetOrigin(origin)

    # Fill with checkerboard pattern
    for z in range(size[2]):
        for y in range(size[1]):
            for x in range(size[0]):
                # Determine which value to use based on position
                checker_value = (
                    x // checker_size + y // checker_size + z // checker_size
                ) % 2
                if checker_value == 0:
                    image[x, y, z] = value1
                else:
                    image[x, y, z] = value2

    return image


def create_ct_hounsfield_image(
    size: Tuple[int, int, int] = (128, 128, 64),
    spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    min_value: float = -1000.0,  # Air in HU
    max_value: float = 3000.0,  # Dense bone in HU
    pixel_type: int = sitk.sitkInt16,
    origin: Tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> sitk.Image:
    """Create a synthetic CT image with Hounsfield Unit-like values.

    Creates a gradient image with values ranging from min_value to max_value
    to simulate a CT image with Hounsfield Units. The image has a central
    sphere with bone-like HU values, surrounded by soft tissue-like values,
    and air-like values at the periphery.

    Parameters
    ----------
    size : Tuple[int, int, int], optional
        Image dimensions in pixels, by default (128, 128, 64)
    spacing : Tuple[float, float, float], optional
        Pixel spacing in physical units, by default (1.0, 1.0, 1.0)
    min_value : float, optional
        Minimum HU value (air), by default -1000.0
    max_value : float, optional
        Maximum HU value (dense bone), by default 3000.0
    pixel_type : int, optional
        SimpleITK pixel type, by default sitk.sitkInt16
    origin : Tuple[float, float, float], optional
        Image origin in physical coordinates, by default (0.0, 0.0, 0.0)

    Returns
    -------
    sitk.Image
        A synthetic CT image with HU-like values

    Notes
    -----
    The image contains regions with values approximating:
    - Air: ~ -1000 HU
    - Fat: ~ -100 to -50 HU
    - Water/Soft tissue: ~ 0 to 100 HU
    - Bone: ~ 300 to 3000 HU

    Examples
    --------
    >>> import SimpleITK as sitk
    >>> from imgtools.datasets.sample_images import (
    ...     create_ct_hounsfield_image,
    ... )
    >>> # Create a synthetic CT image
    >>> ct_image = create_ct_hounsfield_image()
    >>> # Calculate min, max, mean values
    >>> stats = sitk.StatisticsImageFilter()
    >>> stats.Execute(ct_image)
    >>> print(
    ...     f"CT image range: [{stats.GetMinimum():.1f}, {stats.GetMaximum():.1f}]"
    ... )
    CT image range: [-1000.0, 3000.0]
    """
    # Create blank image
    image = sitk.Image(size, pixel_type)
    image.SetSpacing(spacing)
    image.SetOrigin(origin)

    center = [s // 2 for s in size]
    max_distance = math.sqrt(sum((s // 2) ** 2 for s in size))

    # Create a radial pattern with different tissue values
    for z in range(size[2]):
        for y in range(size[1]):
            for x in range(size[0]):
                # Calculate distance from center in pixels
                dx = x - center[0]
                dy = y - center[1]
                dz = z - center[2]
                distance = math.sqrt(dx**2 + dy**2 + dz**2)

                # Normalize distance
                norm_distance = distance / max_distance

                # Different tissue values based on distance from center
                if norm_distance < 0.2:  # Central dense bone
                    value = 1000 + 2000 * (1 - norm_distance / 0.2)
                elif norm_distance < 0.3:  # Less dense bone
                    value = 300 + 700 * (0.3 - norm_distance) / 0.1
                elif norm_distance < 0.6:  # Soft tissue
                    value = -50 + 350 * (0.6 - norm_distance) / 0.3
                elif norm_distance < 0.8:  # Fat
                    value = -100 + 50 * (0.8 - norm_distance) / 0.2
                else:  # Air
                    value = min_value

                # Add some variation
                value += (
                    hash((x, y, z)) % 100 - 50
                )  # Simple deterministic noise
                value = min(max_value, max(min_value, value))  # Clamp values

                image[x, y, z] = int(value)

    return image


if __name__ == "__main__":
    noisy_sphere = create_noisy_sphere_image(
        size=(100, 100, 100),
        spacing=(1.0, 1.0, 1.0),
        radius=20,
        noise_level=0.3,
    )
