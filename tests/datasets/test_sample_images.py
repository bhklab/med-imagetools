"""Tests for the sample_images module which provides synthetic image creation functions."""

import pytest
import numpy as np
import SimpleITK as sitk
from typing import Tuple

from imgtools.datasets.sample_images import (
    create_sphere_image,
    create_grid_image,
    create_gradient_image,
    create_cross_image,
    create_rod_image,
    create_noisy_sphere_image,
    create_checkerboard_image,
    create_ct_hounsfield_image,
)


@pytest.fixture(autouse=True, scope="module")
def suppress_debug_logging():
    """Suppress debug logging for cleaner test output."""
    import logging
    logging.getLogger("imgtools").setLevel(logging.WARNING)


class TestSphereImage:
    """Tests for create_sphere_image function."""
    def test_custom_parameters(self):
        """Test creating a sphere with custom parameters."""
        # Test custom size, spacing, center, radius, values and pixel type
        size = (32, 32, 32)
        spacing = (0.5, 0.5, 0.5)
        center = (10, 15, 20)
        radius = 5.0
        fg = 10.0
        bg = 1.0
        pixel_type = sitk.sitkUInt8
        origin = (10.0, 20.0, 30.0)
        
        image = create_sphere_image(
            size=size, 
            spacing=spacing,
            center=center,
            radius=radius,
            foreground_value=fg,
            background_value=bg,
            pixel_type=pixel_type,
            origin=origin
        )
        
        assert image.GetSize() == size
        assert image.GetSpacing() == spacing
        assert image.GetOrigin() == origin
        assert image.GetPixelID() == pixel_type


class TestGridImage:
    """Tests for create_grid_image function."""

    def test_custom_parameters(self):
        """Test creating a grid with custom parameters."""
        # Test custom grid spacing
        grid_spacing = 4
        fg = 100.0
        bg = -50.0
        image = create_grid_image(
            grid_spacing=grid_spacing,
            foreground_value=fg,
            background_value=bg
        )
        
        # Check grid lines at specified spacing with custom values
        assert image[0, 0, 0] == fg
        assert image[4, 0, 0] == fg
        assert image[0, 4, 0] == fg
        assert image[0, 0, 4] == fg
        assert image[1, 1, 1] == bg


class TestGradientImage:
    """Tests for create_gradient_image function."""

    def test_custom_parameters(self):
        """Test creating gradients with custom parameters."""
        # Test different directions and custom min/max values
        
        # Test y-axis direction
        y_image = create_gradient_image(direction="y")
        assert y_image[32, 0, 32] == pytest.approx(0.0)
        assert y_image[32, 63, 32] == pytest.approx(1.0)
        # Test radial direction
        r_image = create_gradient_image(direction="radial")
        assert r_image[32, 32, 32] == pytest.approx(0.0)  # Center is minimum
        corner_value = r_image[0, 0, 0]
        assert corner_value > 0.5  # Corner should be toward max
        # Test invalid direction raises error
        with pytest.raises(ValueError):
            create_gradient_image(direction="invalid")


class TestCrossImage:
    """Tests for create_cross_image function."""

    def test_custom_parameters(self):
        """Test creating a cross with custom parameters."""
        # Test custom center
        center = (20, 25, 30)
        
        # Test custom thickness
        thickness = 3
        thick_image = create_cross_image(thickness=thickness, center=center)


class TestRodImage:
    """Tests for create_rod_image function."""

    def test_custom_parameters(self):
        """Test creating rods with custom parameters."""

        # Test z-axis direction
        z_image = create_rod_image(axis="z")
        assert z_image[32, 32, 32] == 1.0
        assert z_image[32 + 2, 32 + 2, 32] == 0.0
        
        # Test custom radius
        radius = 3
        radius_image = create_rod_image(radius=radius)
        assert radius_image[32, 32 + 2, 32] == 1.0  # Within radius
        assert radius_image[32, 32 + 4, 32] == 0.0  # Outside radius
        
        # Test invalid axis raises ValueError
        with pytest.raises(ValueError):
            create_rod_image(axis="invalid")

class TestNoisySphereImage:
    """Tests for create_noisy_sphere_image function."""

    def test_custom_noise_levels(self):
        """Test creating spheres with different noise levels."""
        
        # Test high noise level
        high_noise = create_noisy_sphere_image(noise_level=0.5)
        foreground_mask = sitk.Greater(high_noise, 0.0)
        stats = sitk.StatisticsImageFilter()
        stats.Execute(sitk.Mask(high_noise, foreground_mask))
        # Standard deviation should be higher with more noise
        assert stats.GetSigma() > 0.1


class TestCheckerboardImage:
    """Tests for create_checkerboard_image function."""

    def test_custom_parameters(self):
        """Test creating a checkerboard with custom parameters."""
        # Test custom checker size
        checker_size = 4
        checker_image = create_checkerboard_image(checker_size=checker_size)
        
        # Check alternating pattern with smaller checker size
        assert checker_image[0, 0, 0] == 0.0
        assert checker_image[0, 0, 4] == 1.0
        assert checker_image[0, 4, 0] == 1.0
        assert checker_image[4, 0, 0] == 1.0
        

class TestCTHounsfieldImage:
    """Tests for create_ct_hounsfield_image function."""

    def test_custom_parameters(self):
        """Test creating a CT image with custom parameters."""
        # Test custom min/max values
        min_val = -500.0
        max_val = 1500.0
        range_image = create_ct_hounsfield_image(min_value=min_val, max_value=max_val)
        
        stats = sitk.StatisticsImageFilter()
        stats.Execute(range_image)
        assert stats.GetMinimum() >= min_val
        assert stats.GetMaximum() <= max_val
        
        # Test custom pixel type
        pixel_type = sitk.sitkInt32
        pixel_image = create_ct_hounsfield_image(pixel_type=pixel_type)
        assert pixel_image.GetPixelID() == pixel_type