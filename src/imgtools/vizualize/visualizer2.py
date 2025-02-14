from __future__ import annotations

import base64
import math
import time
from dataclasses import dataclass, field
from io import BytesIO
from typing import TYPE_CHECKING, Iterator

import ipywidgets as widgets  # type: ignore
import numpy as np
import SimpleITK as sitk
from IPython.display import display
from matplotlib import pyplot as plt
from matplotlib.pylab import f
from PIL import Image
from tqdm.notebook import tqdm

from imgtools.coretypes import RegionBox
from imgtools.logging import logger
from imgtools.utils import image_to_array

if TYPE_CHECKING:
    from pathlib import Path

    import SimpleITK as sitk

from collections import namedtuple
from enum import Enum


class MaskColor(Enum):
    RED = [255, 0, 0]
    GREEN = [0, 255, 0]
    BLUE = [0, 0, 255]
    YELLOW = [255, 255, 0]
    CYAN = [0, 255, 255]
    MAGENTA = [255, 0, 255]
    WHITE = [255, 255, 255]
    BLACK = [0, 0, 0]
    RGB = [255, 0, 0, 0, 255, 0, 0, 0, 255]


def display_slices(
    array: np.array, x_index: int, y_index: int, z_index: int
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    # plt.imshow
    axes[0].imshow(array[x_index, :, :], aspect="auto")

    axes[1].imshow(array[:, y_index, :], aspect="auto")

    axes[2].imshow(array[:, :, z_index], aspect="auto")

    # turn off axies
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
    main_image: sitk.Image

    @classmethod
    def from_image(
        cls,
        image: sitk.Image,
    ) -> ImageVisualizer:
        return cls(main_image=image)

    @classmethod
    def from_image_and_mask(
        cls,
        image: sitk.Image,
        mask: sitk.Image,
        label: int = 1,
        as_countour: bool = False,
        # overlay settings
        mask_color: MaskColor = MaskColor.GREEN,
        opacity: float = 0.5,
        background_label: int = 0,
        # preprocessing settings
        crop_to_bbox: bool = True,
        croppad: int = 2,
    ) -> ImageVisualizer:
        """Thiis should overlay the mask on the image"""

        region = (
            RegionBox.from_mask_bbox(mask, label=label)
            .expand_to_cube()  # cube expanding will help for grid
            .pad(croppad)
        )

        if as_countour:
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
        return sitk.GetArrayFromImage(self.main_image)

    def view_slices(self) -> SliceWidgets:
        return create_interactive(self.array)

    def view_grid(
        self,
        every: int = 1,
        fig: plt.Figure | None = None,
    ) -> plt.Figure:
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
