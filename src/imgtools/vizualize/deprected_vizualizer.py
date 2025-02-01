"""vizualizer.py: Vizualizer class for visualizing images and their masks."""

# %% Imports
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator

import numpy as np
import SimpleITK as sitk
from matplotlib import pyplot as plt
from PIL import Image

from imgtools.ops import Resize
from imgtools.types import Coordinate, ImageGeometry, ImageOrArray, Size3D, Spacing3D
from imgtools.utils import image_to_array

"""
NOTE: this module sucks lmao. lets just make it straightforward.
"""


@dataclass
class ImageSlicePlots:
    """Class to hold a list of pyplot images of a 3D volume sliced along an axis, optionally with a mask overlay."""

    image_list: list[plt.Figure] = field(default_factory=list)
    mask_list: list[plt.Figure] = field(default_factory=list)

    alpha: float = 0.3
    image_cmap: any = field(default_factory=lambda: plt.cm.Greys_r)
    mask_cmap: any = field(default_factory=lambda: plt.cm.brg)

    @classmethod
    def from_images(
        cls,
        images: np.ndarray,
        masks: np.ndarray | None = None,
        alpha: float = 0.3,
        image_cmap: any = plt.cm.Greys_r,
        mask_cmap: any = plt.cm.brg,
    ) -> ImageSlicePlots:
        """Create an ImageSlicePlots object from a list of numpy arrays."""
        image_list = [plt.figure() for _ in range(images.shape[0])]
        mask_list = [plt.figure() for _ in range(masks.shape[0])] if masks is not None else None

        return cls(
            image_list=image_list,
            mask_list=mask_list,
            alpha=alpha,
            image_cmap=image_cmap,
            mask_cmap=mask_cmap,
        )

    def to_grid(self, ncols: int) -> plt.Figure:
        """Combine the image and mask plots into a single grid."""
        # if there IS a mask, overlay it on the image
        if self.mask_list is not None:
            for i, (image, mask) in enumerate(zip(self.image_list, self.mask_list)):
                plt.figure(image.number)
                plt.imshow(image, cmap=self.image_cmap)
                plt.imshow(mask, cmap=self.mask_cmap, alpha=self.alpha)
                plt.axis("off")
        else:
            for image in self.image_list:
                plt.figure(image.number)
                plt.imshow(image, cmap=self.image_cmap)
                plt.axis("off")

        # Create a grid of images
        nrows = len(self.image_list) // ncols
        fig, axes = plt.subplots(nrows, ncols, figsize=(15, 15))
        for i, ax in enumerate(axes.flat):
            ax.imshow(self.image_list[i])
            ax.axis("off")


@dataclass
class BaseImageVizualizer:
    image: ImageOrArray
    mask: ImageOrArray | None = field(default=None)

    alpha: float = 0.3
    image_cmap: any = field(default_factory=lambda: plt.cm.Greys_r)
    mask_cmap: any = field(default_factory=lambda: plt.cm.brg)

    image_array: np.ndarray = field(init=False)
    mask_array: np.ndarray | None = field(init=False)

    def __post_init__(self):
        self._validate_images()

    def plot_slices(self, every_n: int, axis: int) -> ImageSlicePlots:
        """Plot slices of the image and mask along the specified axis."""
        sliced = self._sliced(every_n, axis)
        return ImageSlicePlots.from_images(
            images=sliced.image_array,
            masks=sliced.mask_array if sliced.mask_array is not None else None,
            alpha=self.alpha,
            image_cmap=self.image_cmap,
            mask_cmap=self.mask_cmap,
        )

    def resize(
        self, size: Size3D | tuple | int | float, interpolation: str = "linear"
    ) -> BaseImageVizualizer:
        """Resize the image and mask to a new size."""
        # resizer = Resize(size, interpolation=interpolation)
        match size:
            case Size3D():
                resizer = Resize(size.as_tuple, interpolation=interpolation)
            case tuple() | int() | float():
                resizer = Resize(size, interpolation=interpolation)

        image = resizer(self.image)
        mask = resizer(self.mask) if self.mask is not None else None
        return BaseImageVizualizer(
            image=image,
            mask=mask,
            alpha=self.alpha,
            image_cmap=self.image_cmap,
            mask_cmap=self.mask_cmap,
        )

    def _sliced(self, every_n: int, axis: int) -> BaseImageVizualizer:
        """Slice images using parameters then return a new Vizualizer."""

        assert isinstance(self.image, sitk.Image), "not implemented for numpy arrays"

        # 1. get the slices (list of sitk.Images)
        # 2. convert to numpy arrays

        axis -= 1  # convert to 0-based index

        image_slices = [
            self._to_array(slice) for slice in self._get_slices(self.image, every_n, axis)
        ]
        mask_slices = (
            [self._to_array(slice) for slice in self._get_slices(self.mask, every_n, axis)]
            if self.mask is not None
            else None
        )
        # Join each 2D slice into a 3D volume ALONG the CORRECT axis
        image_slices_nd = np.stack(image_slices, axis=axis)
        mask_slices_nd = np.stack(mask_slices, axis=axis) if mask_slices is not None else None

        return BaseImageVizualizer(
            image=image_slices_nd,
            mask=mask_slices_nd,
            alpha=self.alpha,
            image_cmap=self.image_cmap,
            mask_cmap=self.mask_cmap,
        )

    @staticmethod
    def _get_slices(
        image: sitk.Image, every_n: int, axis: int
    ) -> Generator[sitk.Image, None, None]:
        for i in range(0, image.GetSize()[axis], every_n):
            yield image[tuple(slice(None) if dim != axis else i for dim in range(3))]

    def _to_array(self, image: ImageOrArray) -> np.ndarray:
        match image:
            case sitk.Image():
                return sitk.GetArrayViewFromImage(image)
            case np.ndarray():
                return image
            case _:
                errmsg = f"Unsupported type: {type(image)}"
                raise TypeError(errmsg)

    def _validate_images(self):
        """Validate the image and mask for compatibility."""
        self.image_array = self._to_array(self.image)
        if self.image_array.ndim != 3:
            raise ValueError(f"Image must have 3 dimensions, got {self.image_array.ndim}")
        if self.mask is None:
            self.mask_array = None
            return

        self.mask_array = self._to_array(self.mask)
        if self.mask_array.ndim != 3:
            raise ValueError(f"Mask must have 3 dimensions, got {self.mask_array.ndim}")
        if self.image_array.shape != self.mask_array.shape:
            errmsg = (
                "Image and mask shapes do not match: "
                f"{self.image_array.shape} != {self.mask_array.shape}"
            )
            raise ValueError(errmsg)

    def __repr__(self):
        image_shape = (
            self.image.shape if isinstance(self.image, np.ndarray) else self.image.GetSize()
        )
        mask_shape = (
            self.mask.shape
            if isinstance(self.mask, np.ndarray)
            else self.mask.GetSize()
            if self.mask is not None
            else None
        )
        return f"BaseImageVizualizer(image_shape={image_shape}, mask_shape={mask_shape})"


from rich import print, progress  # type: ignore # noqa

# Load example images
ct_image = sitk.ReadImage(
    "/home/bioinf/bhklab/radiomics/readii-negative-controls/rawdata/RADCURE/images/niftis/SubjectID-3_RADCURE-4106/CT_70181_original.nii.gz"
)
seg_image = sitk.ReadImage(
    "/home/bioinf/bhklab/radiomics/readii-negative-controls/rawdata/RADCURE/images/niftis/SubjectID-3_RADCURE-4106/RTSTRUCT_54305_GTV.nii.gz"
)

# %% Instantiate the Vizualizer

viz = BaseImageVizualizer(
    image=ct_image,
    mask=seg_image,
    alpha=0.3,
    image_cmap=plt.cm.Greys_r,
    mask_cmap=plt.cm.brg,
)

print("Original:", viz)

print(
    "Resized:",
    viz.resize(
        Size3D(0, 0, 100),
        interpolation="linear",
    ),
)

print(
    "Sliced:",
    viz.plot_slices(
        every_n=10,
        axis=2,
    ),
)
print(
    "Resized and Sliced:",
    viz.resize(
        Size3D(0, 0, 100),
        interpolation="linear",
    )
    .plot_slices(
        every_n=10,
        axis=2,
    )
    .to_grid(5),
)


# %%
