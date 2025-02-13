from __future__ import annotations

import base64
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


def create_interactive(
    array: np.ndarray,
) -> None:
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
        # overlay settings
        mask_color: MaskColor = MaskColor.GREEN,
        opacity: float = 0.5,
        background_label: int = 0,
        # preprocessing settings
        crop_to_bbox: bool = True,
        as_countour: bool = False,
    ) -> ImageVisualizer:
        """Thiis should overlay the mask on the image"""

        region = (
            RegionBox.from_mask_bbox(mask, label=label)
            .expand_to_cube()
            .pad(10)
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

    def view_slices(self) -> None:
        create_interactive(self.array)

    def view_grid(self, cols: int = 5, rows: int = 5, pad: int = 5) -> None:
        nslices = cols * rows
        # figure size should be calculate based on the number of slices
        size_per_slice = 5
        fig_size = (size_per_slice * cols, size_per_slice * rows)
        fig = plt.figure(figsize=fig_size)

        image = self.main_image

        if image.GetPixelID() == 13:
            # Padding values for each spatial dimension (x, y, z), no padding for color channels
            pad_width = (
                (pad, pad),
                (pad, pad),
                (pad, pad),
                (0, 0),
            )  # Padding 10 on each side for x, y, z dimensions

            # Pad with black (0)
            array = sitk.GetArrayFromImage(image)
            padded_array = np.pad(
                array, pad_width=pad_width, mode="constant", constant_values=0
            )
            image = sitk.GetImageFromArray(padded_array, isVector=True)
        else:
            image = sitk.ConstantPad(image, [pad, pad, pad], [pad, pad, pad])

        size = image.GetSize()
        slices = [
            image[:, :, int(round(s))]
            for s in np.linspace(pad, size[2] - pad - 1, nslices)
        ]
        # get the middle nslices slices
        slices = slices[
            len(slices) // 2 - nslices // 2 : len(slices) // 2 + nslices // 2 + 1
        ]

        print(f"Number of slices: {len(slices)}")
        timg = sitk.Tile(slices, [cols, rows, 0])
        print(f"Tile size: {timg.GetSize()}")

        array = sitk.GetArrayFromImage(timg)
        plt.imshow(array, cmap="gray")
