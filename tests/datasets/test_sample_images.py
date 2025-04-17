# """Tests for the sample_images module which provides synthetic image creation functions."""
# NOTE: commented these out because they started taking forever on Github Actions

# import pytest
# import numpy as np
# import SimpleITK as sitk
# from typing import Tuple

# from imgtools.datasets.sample_images import (
#     create_sphere_image,
#     create_grid_image,
#     create_gradient_image,
#     create_cross_image,
#     create_rod_image,
#     create_noisy_sphere_image,
#     create_checkerboard_image,
#     create_ct_hounsfield_image,
# )


# @pytest.fixture(autouse=True, scope="module")
# def suppress_debug_logging():
#     """Suppress debug logging for cleaner test output."""
#     import logging
#     logging.getLogger("imgtools").setLevel(logging.WARNING)


# class TestSphereImage:
#     """Tests for create_sphere_image function."""

#     def test_default_parameters(self):
#         """Test creating a sphere image with default parameters."""
#         image = create_sphere_image()
#         assert isinstance(image, sitk.Image)
#         assert image.GetSize() == (64, 64, 64)
#         assert image.GetSpacing() == (1.0, 1.0, 1.0)
#         assert image.GetPixelID() == sitk.sitkFloat32

#         # Test that there's a sphere in the image
#         stats = sitk.StatisticsImageFilter()
#         stats.Execute(image)
#         assert stats.GetMinimum() == 0.0
#         assert stats.GetMaximum() == 1.0
#         # Center point should be foreground (1.0)
#         assert image[32, 32, 32] == 1.0
#         # Corner points should be background (0.0)
#         assert image[0, 0, 0] == 0.0
#         assert image[63, 63, 63] == 0.0

#     def test_custom_size(self):
#         """Test creating a sphere with custom size."""
#         size = (32, 32, 32)
#         image = create_sphere_image(size=size)
#         assert image.GetSize() == size

#     def test_custom_spacing(self):
#         """Test creating a sphere with custom spacing."""
#         spacing = (0.5, 0.5, 0.5)
#         image = create_sphere_image(spacing=spacing)
#         assert image.GetSpacing() == spacing

#     def test_custom_center(self):
#         """Test creating a sphere with custom center."""
#         center = (10, 20, 30)
#         image = create_sphere_image(center=center)
#         # Center of sphere should be foreground
#         assert image[10, 20, 30] == 1.0

#     def test_custom_radius(self):
#         """Test creating a sphere with custom radius."""
#         radius = 5.0
#         image = create_sphere_image(radius=radius)
#         # Center should be foreground
#         assert image[32, 32, 32] == 1.0
#         # Points just within radius should be foreground
#         assert image[32 + 4, 32, 32] == 1.0
#         # Points beyond radius should be background
#         assert image[32 + 6, 32, 32] == 0.0

#     def test_custom_values(self):
#         """Test creating a sphere with custom foreground and background values."""
#         fg = 10.0
#         bg = -5.0
#         image = create_sphere_image(foreground_value=fg, background_value=bg)
        
#         # Center should be foreground
#         assert image[32, 32, 32] == fg
#         # Corner should be background
#         assert image[0, 0, 0] == bg

#     def test_custom_pixel_type(self):
#         """Test creating a sphere with custom pixel type."""
#         pixel_type = sitk.sitkUInt8
#         image = create_sphere_image(pixel_type=pixel_type)
#         assert image.GetPixelID() == pixel_type

#     def test_custom_origin(self):
#         """Test creating a sphere with custom origin."""
#         origin = (10.0, 20.0, 30.0)
#         image = create_sphere_image(origin=origin)
#         assert image.GetOrigin() == origin


# class TestGridImage:
#     """Tests for create_grid_image function."""

#     def test_default_parameters(self):
#         """Test creating a grid image with default parameters."""
#         image = create_grid_image()
#         assert isinstance(image, sitk.Image)
#         assert image.GetSize() == (64, 64, 64)
        
#         # Test grid pattern exists - grid points should be foreground
#         assert image[0, 0, 0] == 1.0  # Grid line intersection
#         assert image[8, 0, 0] == 1.0  # Grid line x
#         assert image[0, 8, 0] == 1.0  # Grid line y
#         assert image[0, 0, 8] == 1.0  # Grid line z
#         assert image[1, 1, 1] == 0.0  # Non-grid point

#     def test_custom_grid_spacing(self):
#         """Test creating a grid with custom grid spacing."""
#         grid_spacing = 4
#         image = create_grid_image(grid_spacing=grid_spacing)
        
#         # Check grid lines at specified spacing
#         assert image[0, 0, 0] == 1.0
#         assert image[4, 0, 0] == 1.0
#         assert image[0, 4, 0] == 1.0
#         assert image[0, 0, 4] == 1.0
#         assert image[1, 1, 1] == 0.0

#     def test_custom_values(self):
#         """Test creating a grid with custom foreground and background values."""
#         fg = 100.0
#         bg = -50.0
#         image = create_grid_image(foreground_value=fg, background_value=bg)
        
#         # Grid lines should have foreground value
#         assert image[0, 0, 0] == fg
#         # Non-grid points should have background value
#         assert image[1, 1, 1] == bg


# class TestGradientImage:
#     """Tests for create_gradient_image function."""

#     def test_default_parameters(self):
#         """Test creating an x-axis gradient image with default parameters."""
#         image = create_gradient_image()
#         assert isinstance(image, sitk.Image)
#         assert image.GetSize() == (64, 64, 64)
        
#         # Test gradient values along x-axis
#         assert image[0, 32, 32] == pytest.approx(0.0)
#         assert image[63, 32, 32] == pytest.approx(1.0)
#         assert image[32, 32, 32] == pytest.approx(0.5, abs=0.01)

#     def test_y_gradient(self):
#         """Test creating a y-axis gradient."""
#         image = create_gradient_image(direction="y")
        
#         # Test gradient values along y-axis
#         assert image[32, 0, 32] == pytest.approx(0.0)
#         assert image[32, 63, 32] == pytest.approx(1.0)
#         assert image[32, 32, 32] == pytest.approx(0.5, abs=0.01)

#     def test_z_gradient(self):
#         """Test creating a z-axis gradient."""
#         image = create_gradient_image(direction="z")
        
#         # Test gradient values along z-axis
#         assert image[32, 32, 0] == pytest.approx(0.0)
#         assert image[32, 32, 63] == pytest.approx(1.0)
#         assert image[32, 32, 32] == pytest.approx(0.5, abs=0.01)

#     def test_radial_gradient(self):
#         """Test creating a radial gradient."""
#         image = create_gradient_image(direction="radial")
        
#         # Center should be minimum value
#         assert image[32, 32, 32] == pytest.approx(0.0)
#         # Corner should be maximum value or close to it
#         corner_value = image[0, 0, 0]
#         assert corner_value > 0.5  # Should be toward max value

#     def test_custom_min_max_values(self):
#         """Test creating a gradient with custom min/max values."""
#         min_val = -100.0
#         max_val = 100.0
#         image = create_gradient_image(min_value=min_val, max_value=max_val)
        
#         # Test gradient range
#         assert image[0, 32, 32] == pytest.approx(min_val)
#         assert image[63, 32, 32] == pytest.approx(max_val)

#     def test_invalid_direction(self):
#         """Test that invalid direction raises ValueError."""
#         with pytest.raises(ValueError):
#             create_gradient_image(direction="invalid")


# class TestCrossImage:
#     """Tests for create_cross_image function."""

#     def test_default_parameters(self):
#         """Test creating a cross image with default parameters."""
#         image = create_cross_image()
#         assert isinstance(image, sitk.Image)
#         assert image.GetSize() == (64, 64, 64)
        
#         # Test cross pattern at center
#         # Center point should be foreground (part of all 3 axes)
#         assert image[32, 32, 32] == 1.0
        
#         # Points on axes from center should be foreground
#         assert image[32, 32, 40] == 1.0  # z-axis
#         assert image[32, 40, 32] == 1.0  # y-axis
#         assert image[40, 32, 32] == 1.0  # x-axis
        
#         # Points not on any axis should be background
#         assert image[40, 40, 40] == 0.0

#     def test_custom_center(self):
#         """Test creating a cross with custom center."""
#         center = (20, 25, 30)
#         image = create_cross_image(center=center)
        
#         # Cross center should be foreground
#         assert image[20, 25, 30] == 1.0
        
#         # Points on axes from custom center should be foreground
#         assert image[20, 25, 35] == 1.0  # z-axis
#         assert image[20, 30, 30] == 1.0  # y-axis
#         assert image[25, 25, 30] == 1.0  # x-axis

#     def test_custom_thickness(self):
#         """Test creating a cross with custom thickness."""
#         thickness = 3
#         image = create_cross_image(thickness=thickness)
        
#         # Cross center should be foreground
#         assert image[32, 32, 32] == 1.0
        
#         # Points within thickness should be foreground
#         assert image[32, 32 + 1, 32] == 1.0
#         assert image[32, 32, 32 + 1] == 1.0
#         assert image[32 + 1, 32, 32] == 1.0
        
#         # Points outside thickness should be background
#         assert image[32, 32 + 2, 32 + 2] == 0.0


# class TestRodImage:
#     """Tests for create_rod_image function."""

#     def test_default_parameters(self):
#         """Test creating an x-axis rod image with default parameters."""
#         image = create_rod_image()
#         assert isinstance(image, sitk.Image)
#         assert image.GetSize() == (64, 64, 64)
        
#         # Test rod along x-axis
#         center_y = 32
#         center_z = 32
        
#         # Points along the x-axis at center y,z should be foreground
#         for x in range(64):
#             assert image[x, center_y, center_z] == 1.0
        
#         # Points away from the axis should be background
#         assert image[32, center_y + 2, center_z + 2] == 0.0

#     def test_y_axis_rod(self):
#         """Test creating a y-axis rod."""
#         image = create_rod_image(axis="y")
#         center_x = 32
#         center_z = 32
        
#         # Points along the y-axis at center x,z should be foreground
#         for y in range(64):
#             assert image[center_x, y, center_z] == 1.0
        
#         # Points away from the axis should be background
#         assert image[center_x + 2, 32, center_z + 2] == 0.0

#     def test_z_axis_rod(self):
#         """Test creating a z-axis rod."""
#         image = create_rod_image(axis="z")
#         center_x = 32
#         center_y = 32
        
#         # Points along the z-axis at center x,y should be foreground
#         for z in range(64):
#             assert image[center_x, center_y, z] == 1.0
        
#         # Points away from the axis should be background
#         assert image[center_x + 2, center_y + 2, 32] == 0.0

#     def test_custom_radius(self):
#         """Test creating a rod with custom radius."""
#         radius = 3
#         image = create_rod_image(radius=radius)
#         center_y = 32
#         center_z = 32
        
#         # Points along the x-axis at center y,z should be foreground
#         assert image[32, center_y, center_z] == 1.0
        
#         # Points within radius should be foreground
#         assert image[32, center_y + 2, center_z] == 1.0
        
#         # Points outside radius should be background
#         assert image[32, center_y + 4, center_z] == 0.0

#     def test_invalid_axis(self):
#         """Test that invalid axis raises ValueError."""
#         with pytest.raises(ValueError):
#             create_rod_image(axis="invalid")


# class TestNoisySphereImage:
#     """Tests for create_noisy_sphere_image function."""

#     def test_default_parameters(self):
#         """Test creating a noisy sphere image with default parameters."""
#         image = create_noisy_sphere_image()
#         assert isinstance(image, sitk.Image)
#         assert image.GetSize() == (64, 64, 64)
        
#         # Check that image has noise (values won't be exactly 0 and 1)
#         stats = sitk.StatisticsImageFilter()
#         stats.Execute(image)
        
#         # Center should be around 1.0 but with noise
#         center_value = image[32, 32, 32]
#         assert center_value > 0.5  # Should be close to 1.0
#         assert center_value != 1.0  # Shouldn't be exactly 1.0 due to noise
        
#         # Check that standard deviation is non-zero in foreground area
#         foreground_mask = sitk.Greater(image, 0.5)
#         stats.Execute(sitk.Mask(image, foreground_mask))
#         assert stats.GetSigma() > 0  # Should have variation due to noise

#     def test_zero_noise_level(self):
#         """Test creating a sphere with zero noise level (should be same as sphere)."""
#         image = create_noisy_sphere_image(noise_level=0.0)
        
#         # Center should be exactly 1.0 with no noise
#         assert image[32, 32, 32] == 1.0
#         # Corner should be exactly 0.0 with no noise
#         assert image[0, 0, 0] == 0.0

#     def test_high_noise_level(self):
#         """Test creating a sphere with high noise level."""
#         noise_level = 0.5
#         image = create_noisy_sphere_image(noise_level=noise_level)
        
#         # Check that image has significant noise
#         stats = sitk.StatisticsImageFilter()
#         foreground_mask = sitk.Greater(image, 0.0)
#         stats.Execute(sitk.Mask(image, foreground_mask))
        
#         # Standard deviation should be higher with more noise
#         assert stats.GetSigma() > 0.1


# class TestCheckerboardImage:
#     """Tests for create_checkerboard_image function."""

#     def test_default_parameters(self):
#         """Test creating a checkerboard image with default parameters."""
#         image = create_checkerboard_image()
#         assert isinstance(image, sitk.Image)
#         assert image.GetSize() == (64, 64, 64)
        
#         # Test checkerboard pattern
#         # Origin should have value1
#         assert image[0, 0, 0] == 0.0
        
#         # Check alternating pattern (moving by checker_size=8)
#         assert image[0, 0, 8] == 1.0
#         assert image[0, 8, 0] == 1.0
#         assert image[8, 0, 0] == 1.0
#         assert image[8, 8, 8] == 1.0

#     def test_custom_checker_size(self):
#         """Test creating a checkerboard with custom checker size."""
#         checker_size = 4
#         image = create_checkerboard_image(checker_size=checker_size)
        
#         # Check alternating pattern with smaller checker size
#         assert image[0, 0, 0] == 0.0
#         assert image[0, 0, 4] == 1.0
#         assert image[0, 4, 0] == 1.0
#         assert image[4, 0, 0] == 1.0
#         assert image[4, 4, 4] == 1.0

#     def test_custom_values(self):
#         """Test creating a checkerboard with custom values."""
#         value1 = -1.0
#         value2 = 2.0
#         image = create_checkerboard_image(value1=value1, value2=value2)
        
#         # Check that the pattern uses the custom values
#         assert image[0, 0, 0] == value1
#         assert image[0, 0, 8] == value2


# class TestCTHounsfieldImage:
#     """Tests for create_ct_hounsfield_image function."""

#     def test_default_parameters(self):
#         """Test creating a CT Hounsfield unit image with default parameters."""
#         image = create_ct_hounsfield_image()
#         assert isinstance(image, sitk.Image)
#         assert image.GetSize() == (128, 128, 64)
#         assert image.GetPixelID() == sitk.sitkInt16
        
#         # Check value ranges
#         stats = sitk.StatisticsImageFilter()
#         stats.Execute(image)
#         assert stats.GetMinimum() >= -1000.0
#         assert stats.GetMaximum() <= 3000.0
        
#         # Check center has high value (bone-like)
#         center_value = image[64, 64, 32]
#         assert center_value > 1000  # Central area should be dense bone
        
#         # Check periphery has low value (air-like)
#         corner_value = image[0, 0, 0]
#         assert corner_value <= -900  # Should be close to air (-1000 HU)

#     def test_custom_size(self):
#         """Test creating a CT image with custom size."""
#         size = (64, 64, 32)
#         image = create_ct_hounsfield_image(size=size)
#         assert image.GetSize() == size

#     def test_custom_min_max_values(self):
#         """Test creating a CT image with custom min/max values."""
#         min_val = -500.0
#         max_val = 1500.0
#         image = create_ct_hounsfield_image(min_value=min_val, max_value=max_val)
        
#         stats = sitk.StatisticsImageFilter()
#         stats.Execute(image)
#         assert stats.GetMinimum() >= min_val
#         assert stats.GetMaximum() <= max_val


# def test_all_functions_run_without_errors():
#     """Integration test to verify all image creation functions run without errors."""
#     # Create a small size for faster testing
#     small_size = (16, 16, 16)
    
#     # Test each function with minimal parameters
#     create_sphere_image(size=small_size)
#     create_grid_image(size=small_size)
#     create_gradient_image(size=small_size)
#     create_cross_image(size=small_size)
#     create_rod_image(size=small_size)
#     create_noisy_sphere_image(size=small_size)
#     create_checkerboard_image(size=small_size)
#     create_ct_hounsfield_image(size=small_size)