"""3DSliceImages: Efficiently generate and store 2D slices from a 3D SimpleITK image."""

# %%
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator

import ipywidgets as widgets  # type: ignore
import numpy as np
import SimpleITK as sitk
from IPython.display import display
from PIL import Image, ImageDraw, ImageFont
from tqdm.notebook import tqdm

from imgtools import Size3D
from imgtools.logging import logger
from imgtools.ops import Resize
from imgtools.utils import image_to_array

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class ImageSlices:
    image_list: list[Image.Image] = field(default_factory=list)

    @classmethod
    def from_dict(
        cls, slices: dict[tuple[int, int], Image.Image]
    ) -> "ImageSlices":
        image_list = [slices[key] for key in sorted(slices.keys())]
        return cls(image_list)

    def export_gif(self, output_path: Path) -> Path:
        self.image_list[0].save(
            output_path,
            save_all=True,
            append_images=self.image_list[1:],
            duration=100,
            loop=0,
        )
        return output_path

    def export_pngs(self, output_dir: Path) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        for i, image in enumerate(self.image_list):
            file_path = output_dir / f"slice_{i}.png"
            image.save(file_path)
            paths.append(file_path)
        return paths

    def __getitem__(self, index: int) -> Image.Image:
        return self.image_list[index]

    def __len__(self) -> int:
        return len(self.image_list)

    def __iter__(self) -> Iterator[Image.Image]:
        return iter(self.image_list)


def _generate_slice(
    index: int,
    img_slice: np.ndarray,
    mask_slice: np.ndarray | None,
    alpha: float,
    vmax: int,
    vmin: int,
    scale_factor: float = 2.0,
) -> tuple[int, Image.Image]:
    """Generate a single 2D slice, overlaying the mask in red if available,
    with metadata text in the bottom right corner.
    """

    # Normalize the image to 0-255
    img_slice = np.clip(
        (img_slice - vmin) / (vmax - vmin) * 255, 0, 255
    ).astype(np.uint8)

    # Convert image slice to PIL image (grayscale → RGB)
    image = Image.fromarray(img_slice, mode="L").convert("RGB")

    if mask_slice is not None:
        # mask should be all 1s and 0s
        red_mask = np.zeros_like(mask_slice, dtype=np.uint8)

        # Set red channel to 255 where mask values are > 0
        red_mask[mask_slice > 0] = 255
        green_mask = np.zeros_like(mask_slice, dtype=np.uint8)
        blue_mask = np.zeros_like(mask_slice, dtype=np.uint8)

        # Stack the channels to create an RGB image
        mask_img_stack = np.stack([red_mask, green_mask, blue_mask], axis=-1)

        # Convert to PIL image
        mask_img = Image.fromarray(mask_img_stack, mode="RGB")

        # Create an alpha transparency mask where mask values are > 0
        mask_alpha = Image.fromarray(
            (mask_slice > 0).astype(np.uint8) * int(255 * alpha), mode="L"
        )

        # Blend the red mask with the original image
        image = Image.composite(mask_img, image, mask_alpha)

    # Metadata text
    metadata_dict = {
        "Slice #": index,
        "Shape": f"{image.width}x{image.height}",
        "Min": img_slice.min(),
        "Max": img_slice.max(),
    }
    metadata_str = "\n".join(
        [f"{key}: {value}" for key, value in metadata_dict.items()]
    )

    # Draw the text on the image
    draw = ImageDraw.Draw(image)

    font_size = max(10, min(image.width, image.height) * 0.03)
    font = ImageFont.load_default(font_size)

    # Get text size
    text_bbox = draw.textbbox((0, 0), metadata_str, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Calculate position in bottom right
    padding = 10
    position = (
        image.width - text_width - padding,
        image.height - text_height - padding,
    )

    # Add background for better visibility
    bg_padding = 5
    bg_position = (
        position[0] - bg_padding,
        position[1] - bg_padding,
        position[0] + text_width + bg_padding,
        position[1] + text_height + bg_padding,
    )
    draw.rectangle(
        bg_position, fill=(0, 0, 0, 150)
    )  # Semi-transparent background

    # Draw text
    draw.text(position, metadata_str, fill="white", font=font)

    return index, image


@dataclass
class SliceImage3D:
    """Generates 2D slices from a 3D SimpleITK image and optionally overlays a mask."""

    image: sitk.Image
    mask: sitk.Image | None = None

    resizer_interpolation: str = field(
        default="nearest",
        metadata={"choices": ["linear", "nearest", "bspline"]},
    )
    alpha: float = 0.4

    slices: ImageSlices = field(init=False)
    cropped_size: Size3D = field(default_factory=lambda: Size3D(512, 512, 0))

    image_array: np.ndarray = field(init=False)
    mask_array: np.ndarray | None = field(init=False)

    def __post_init__(self) -> None:
        resizer = Resize(
            size=list(self.cropped_size),
            interpolation=self.resizer_interpolation,
            anti_alias=True,
            anti_alias_sigma=2.0,  # Higher value to better prevent artifacts
        )
        logger.debug(f"Resizing image to {self.cropped_size}")
        self.image = resizer(self.image)
        self.image_array, *_image = image_to_array(self.image)

        # Resize mask if provided
        if self.mask:
            self.mask = resizer(self.mask)
            self.mask_array, *_ = image_to_array(self.mask)
        else:
            self.mask_array = None

    def image_slices(self, dim: int, every_n: int = 5) -> list[np.ndarray]:
        return [
            np.take(self.image_array, i, axis=dim)
            for i in range(0, self.image_array.shape[dim], every_n)
        ]

    def mask_slices(
        self, dim: int, every_n: int = 5
    ) -> list[np.ndarray] | None:
        if self.mask_array is not None:
            return [
                np.take(self.mask_array, i, axis=dim)
                for i in range(0, self.mask_array.shape[dim], every_n)
            ]
        return None

    @property
    def vmax(self) -> int:
        return max(
            self.image_array.max(),
            self.mask_array.max() if self.mask_array is not None else 0,
        )

    @property
    def vmin(self) -> int:
        return min(
            self.image_array.min(),
            self.mask_array.min() if self.mask_array is not None else 0,
        )

    def generate_dim_slices(
        self, dim: int, every_n: int = 5, new_size_factor: float = 1.0
    ) -> SliceImage3D:
        """Generate 2D slices along a given dimension, optionally overlaying the mask."""
        slices = self.image_slices(dim, every_n)
        mask_slices: list[np.ndarray] | None = self.mask_slices(dim, every_n)

        if mask_slices is None:
            mask_slices = [np.zeros_like(slices[0])] * len(slices)

        tasks = [
            (
                i,
                img,
                mask,
                self.alpha,
                self.vmax,
                self.vmin,
                new_size_factor,
            )
            for i, (img, mask) in enumerate(
                zip(slices, mask_slices, strict=False)
            )
        ]
        start = time.time()
        results = [_generate_slice(*task) for task in tqdm(tasks)]
        logger.info(f"Time taken: {time.time() - start:.2f}s")

        # Store slices in a dictionary
        images = [image for _, image in results]
        self.slices = ImageSlices(images)

        return self

    def __repr__(self) -> str:
        slices_by_dimension = {
            dim: len(self.image_slices(dim)) for dim in range(3)
        }
        return (
            f"SliceImage3D(image_shape={self.image_array.shape}, "
            f"slices_by_dimension={slices_by_dimension})"
        )

    def view(self) -> None:
        def display_slice(index: int) -> None:
            img = self.slices[index]
            display(img)

        max_slider = len(self.slices) - 1
        widgets.interact(
            display_slice,
            index=widgets.IntSlider(min=0, max=max_slider, step=1, value=0),
        )


# %%
if __name__ == "__main__":  # pragma: no cover
    from rich import print, progress  # type: ignore # noqa
    from imgtools.coretypes.box import RegionBox
    from pathlib import Path

    # ct_path =    "/home/bioinf/bhklab/radiomics/readii-negative-controls/rawdata/RADCURE/images/niftis/SubjectID-3_RADCURE-4106/CT_70181_original.nii.gz"
    # seg_path =     "/home/bioinf/bhklab/radiomics/readii-negative-controls/rawdata/RADCURE/images/niftis/SubjectID-3_RADCURE-4106/RTSTRUCT_54305_GTV.nii.gz"
    image_dir = (
        Path("/home/bioinf/bhklab/radiomics/repos/med-imagetools")
        / "notebooks"
    )
    ct_path = image_dir / "merged_duck_with_star.nii.gz"
    seg_path = image_dir / "star_mask.nii.gz"

    setting = 2
    dim = 0

    # Load example images
    ct_image = sitk.ReadImage(ct_path)
    seg_image = sitk.ReadImage(seg_path)
    match setting:
        case 1:
            bbox = RegionBox.from_mask_bbox(seg_image).minimum_dimension_size(
                25
            )
            cropped_image = bbox.crop_image(ct_image)
            cropped_mask = bbox.crop_image(seg_image)
        case 2:
            cropped_image = ct_image
            cropped_mask = seg_image

    new_size = 512 * 2

    slices = SliceImage3D(
        cropped_image,
        mask=cropped_mask,
        cropped_size=Size3D(new_size, new_size, 0),
    )

    # %%
    slices.generate_dim_slices(dim, every_n=1).view()

# %%
