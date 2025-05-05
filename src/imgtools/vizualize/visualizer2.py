from __future__ import annotations

import math
from collections import namedtuple
from dataclasses import dataclass
from enum import Enum

import ipywidgets as widgets  # type: ignore
import numpy as np
import SimpleITK as sitk
from matplotlib import pyplot as plt

from imgtools.coretypes import RegionBox


class MaskColor(Enum):
    """Predefined color values for mask overlays.

    Each color is represented as an RGB list with values from 0-255.
    The RGB value specifically contains concatenated R, G, B channels for sitk colormap.
    """

    RED = [255, 0, 0]
    GREEN = [0, 255, 0]
    BLUE = [0, 0, 255]
    YELLOW = [255, 255, 0]
    CYAN = [0, 255, 255]
    MAGENTA = [255, 0, 255]


def display_slices(
    array: np.ndarray, x_index: int, y_index: int, z_index: int
) -> None:
    """Display orthogonal slices of a 3D array.

    Parameters
    ----------
    array : np.ndarray
        3D numpy array representing the image volume
    x_index : int
        Index for slice in the x dimension
    y_index : int
        Index for slice in the y dimension
    z_index : int
        Index for slice in the z dimension
    """
    if not isinstance(array, np.ndarray):
        raise TypeError("Input must be a numpy array")

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes[0].imshow(array[x_index, :, :], aspect="auto")
    axes[1].imshow(array[:, y_index, :], aspect="auto")
    axes[2].imshow(array[:, :, z_index], aspect="auto")
    # turn off axes
    for ax in axes:
        ax.axis("off")

    plt.show()
    for ax in axes:
        ax.axis("off")

    plt.show()


SliceWidgets = namedtuple("SliceWidgets", ["x", "y", "z"])


def create_interactive(
    array: np.ndarray,
) -> SliceWidgets:
    x = widgets.IntSlider(
        min=0, max=array.shape[0] - 1, value=0, description="X Slice"
    )
    y = widgets.IntSlider(
        min=0, max=array.shape[1] - 1, value=0, description="Y Slice"
    )
    z = widgets.IntSlider(
        min=0, max=array.shape[2] - 1, value=0, description="Z Slice"
    )

    widgets.interact(
        display_slices,
        x_index=x,
        y_index=y,
        z_index=z,
        array=widgets.fixed(array),
    )

    return SliceWidgets(x=x, y=y, z=z)


@dataclass
class ImageVisualizer:
    """Simple visualizer for sitk based images."""

    main_image: sitk.Image

    @classmethod
    def from_image(
        cls,
        image: sitk.Image,
    ) -> ImageVisualizer:
        """Create an ImageVisualizer from a SimpleITK image."""

        return cls(main_image=image)

    @classmethod
    def from_image_and_mask(
        cls,
        image: sitk.Image,
        mask: sitk.Image,
        label: int = 1,
        as_contour: bool = False,
        # overlay settings
        mask_color: MaskColor = MaskColor.GREEN,
        opacity: float = 0.5,
        background_label: int = 0,
        # preprocessing settings
        crop_to_bbox: bool = True,
        croppad: int = 2,
    ) -> ImageVisualizer:
        """Create an ImageVisualizer with a mask overlay on the image.

        Parameters
        ----------
        image : sitk.Image
            Base image for visualization
        mask : sitk.Image
            Mask image to overlay on the base image
        label : int, default=1
            Label value in the mask to use for overlay
        as_contour : bool, default=False
            If True, convert the mask to a contour before overlay
        mask_color : MaskColor, default=MaskColor.GREEN
            Color to use for the mask overlay
        opacity : float, default=0.5
            Opacity of the mask overlay (0.0-1.0)
        background_label : int, default=0
            Label value in the mask to treat as background
        crop_to_bbox : bool, default=True
            If True, crop the image to the bounding box of the mask
        croppad : int, default=2
            Padding to add around the crop region

        Returns
        -------
        ImageVisualizer
            Instance with the mask overlaid on the image
        """

        region = (
            RegionBox.from_mask_bbox(mask, label=label)
            .expand_to_cube()  # cube expanding will help for grid
            .pad(croppad)
        )

        if as_contour:
            f_mask = sitk.BinaryContour(mask, fullyConnected=True)
        else:
            f_mask = mask

        combined_image = sitk.LabelOverlay(
            sitk.Cast(image, pixelID=sitk.sitkUInt8),
            f_mask,
            opacity=opacity,
            backgroundValue=background_label,
            colormap=mask_color.value,
        )

        if crop_to_bbox:
            combined_image = region.crop_image(combined_image)

        return cls(main_image=combined_image)

    @property
    def array(self) -> np.ndarray:
        return sitk.GetArrayViewFromImage(self.main_image)

    def view_slices(self) -> SliceWidgets:
        return create_interactive(self.array)

    def view_grid(
        self,
        every: int = 1,
        fig: plt.Figure | None = None,
    ) -> plt.Figure:
        """Visualize slices in a grid.

        Parameters
        ----------
        every : int
            Step size for slice selection
        fig : plt.Figure, optional
            Existing figure to use for visualization
            If None, a new figure will be created

        Returns
        -------
        plt.Figure
            Figure containing the grid of slices
        """
        dimension = 2
        plot_size = 3

        image = self.main_image
        size = image.GetSize()

        slice_indices = list(range(0, size[dimension], every))

        # should be a square number of slices
        cols = math.ceil(np.sqrt(len(slice_indices)))
        rows = math.ceil(len(slice_indices) / cols)
        figsize = (plot_size * cols, plot_size * rows)

        if fig is None:
            fig, axes = plt.subplots(
                rows, cols, figsize=figsize, constrained_layout=True
            )
        else:
            axes = fig.subplots(rows, cols)

        axes = axes.ravel()

        for idx, slice_index in enumerate(slice_indices):
            slice_image = image[:, :, slice_index]
            array = sitk.GetArrayViewFromImage(slice_image)

            ax = axes[idx]
            ax.imshow(array, cmap="gray")
            ax.set_title(f"Slice {slice_index + 1}/{size[2]}", fontsize=8)
            ax.axis("off")

        # Hide any extra axes if the grid is larger than the number of slices
        for idx in range(len(slice_indices), rows * cols):
            axes[idx].axis("off")

        return fig


if __name__ == "__main__":  # pragma: no cover
    from imgtools.datasets.examples import data_images

    # Load example images
    ct_image = data_images()["duck"]

    viz = ImageVisualizer.from_image(ct_image)

    viz.view_slices()
