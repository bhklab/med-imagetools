"""3DSliceImages: Efficiently generate and store 2D slices from a 3D SimpleITK image."""

# %%
from __future__ import annotations

import base64
import time
from dataclasses import dataclass, field
from io import BytesIO
from typing import TYPE_CHECKING, Iterator

import ipywidgets as widgets  # type: ignore
import numpy as np
from IPython.display import display
from PIL import Image
from tqdm.notebook import tqdm

from imgtools.loggers import logger
from imgtools.utils import image_to_array

if TYPE_CHECKING:
    from pathlib import Path

    import SimpleITK as sitk

__all__: list[str] = [
    "ImageSlices",
    "SliceImage3D",
    "view_multiple_SliceImage3DObjects",
]


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


@dataclass
class SliceImage3D:
    """Generates 2D slices from a 3D SimpleITK image and optionally overlays a mask."""

    image: sitk.Image
    mask: sitk.Image | None = None
    alpha: float = 0.2
    disable_progress: bool = False

    slices: ImageSlices = field(init=False)
    image_array: np.ndarray = field(init=False)
    mask_array: np.ndarray | None = field(init=False)

    def __post_init__(self) -> None:
        logger.info("Original image shape: " + str(self.image.GetSize()))

        self.image_array, *_image = image_to_array(self.image)

        if self.mask:
            self.mask_array, *_mask = image_to_array(self.mask)
        else:
            self.mask_array = None

        logger.info(f"Image shape: {self.image_array.shape}")
        if self.mask_array is not None:
            logger.info(f"Mask shape: {self.mask_array.shape}")

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

    def generate_dim_slices(
        self,
        dim: int,
        every_n: int = 5,
    ) -> SliceImage3D:
        """Generate 2D slices along a given dimension, optionally overlaying the mask.

        Parameters
        ----------
        dim : int
            The dimension along which to generate slices (0, 1, or 2).
        every_n : int, optional
            Generate a slice every `every_n` pixels, by default 5.
        """
        slices = self.image_slices(dim, every_n)
        mask_slices: list[np.ndarray] | None = self.mask_slices(dim, every_n)

        if mask_slices is None:
            mask_slices = [
                np.zeros_like(slices[0]) for _ in range(len(slices))
            ]
        logger.warning("Generating slices...")
        tasks = [
            (
                i,
                img,
                mask,
                self.alpha,
                self.vmax,
                self.vmin,
            )
            for i, (img, mask) in enumerate(
                zip(slices, mask_slices, strict=False)
            )
        ]
        start = time.time()
        results = [
            SliceImage3D._generate_slice(*task)
            for task in tqdm(tasks, disable=self.disable_progress)
        ]
        logger.info(f"Time taken: {time.time() - start:.2f}s")

        # Store slices in a dictionary
        images = [image for _, image in results]
        self.slices = ImageSlices(images)

        return self

    @staticmethod
    def _generate_slice(
        index: int,
        img_slice: np.ndarray,
        mask_slice: np.ndarray | None,
        alpha: float,
        vmax: int,
        vmin: int,
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
            blue_mask = np.zeros_like(mask_slice, dtype=np.uint8)

            green_mask = np.clip(mask_slice * 255, 0, 255).astype(np.uint8)

            # Stack the channels to create an RGB image
            mask_img_stack = np.stack(
                [red_mask, green_mask, blue_mask], axis=-1
            )

            # Convert to PIL image
            mask_img = Image.fromarray(mask_img_stack, mode="RGB")

            # Create an alpha transparency mask where the mask_image is not black and multiply by alpha
            mask_alpha = Image.fromarray(
                np.clip(mask_slice * 255 * alpha, 0, 255).astype(np.uint8),
                mode="L",
            )

            # Blend the red mask with the original image
            image = Image.composite(mask_img, image, mask_alpha)

        return index, image

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
            index=widgets.IntSlider(
                min=0, max=max_slider, step=1, value=max_slider // 2
            ),
        )


def view_multiple_SliceImage3DObjects(*args: tuple[str, SliceImage3D]) -> None:  # noqa
    """This is a grand view to help when you want to view multiple

    pass in all of them, with generate_dim_slices already called
    ALL of them MUST have the same number of slices
    this will then use a SINGLE slider, to view and iterate over all of them

    """

    # calculate some metadata for all the slices
    metadata_dict = {
        name: f"Shape : x={slice_image.image_array.shape[2]}, y={slice_image.image_array.shape[1]}"
        for name, slice_image in args
    }

    def display_slices(index: int) -> None:
        # Create a vertical box layout for each slice with a label
        vboxes = []
        for name, slice_image in args:
            # Convert the Pillow image to Base64
            buffer = BytesIO()
            slice_image.slices[index].save(buffer, format="PNG")
            base64_image = base64.b64encode(buffer.getvalue()).decode()

            metadata_str = metadata_dict[name]
            # Generate HTML content with Base64-encoded image
            html_content = f"""
            <div style="text-align: center;">
                <h3>{name}</h3>
                <p>{metadata_str}</p>
                <img src="data:image/png;base64,{base64_image}" 
                    style="width: 500px; height: auto;">
            </div>
            """
            vbox = widgets.VBox([widgets.HTML(html_content)])
            vboxes.append(vbox)

        # Create a horizontal box layout for all vboxes
        hbox = widgets.HBox(vboxes)
        display(hbox)

    if not args:
        raise ValueError("At least one SliceImage3D object must be provided")

    num_slices = len(args[0][1].slices)
    if not all(
        len(slice_image.slices) == num_slices for _, slice_image in args
    ):
        errmsg = (
            "All SliceImage3D objects must have the same number of slices!!"
            f" (expected {num_slices}) but got {[len(s.slices) for _, s in args]}"
        )
        raise ValueError(errmsg)

    max_slider = num_slices - 1
    widgets.interact(
        display_slices,
        index=widgets.IntSlider(
            min=0, max=max_slider, step=1, value=max_slider // 2
        ),
    )


# %%
if __name__ == "__main__":  # pragma: no cover
    from rich import print, progress  # type: ignore # noqa
    from imgtools.coretypes.box import RegionBox, Size3D
    from imgtools.datasets.examples import data_images

    # from imgtools.ops.functional import resize

    logger.setLevel("DEBUG")  # type: ignore

    setting = 1
    dim = 0
    every = 5

    # Load example images
    ct_image = data_images()["duck"]
    seg_image = data_images()["mask"]

    # ct_image = resize(
    #     ct_image, size=np.array([512, 512, 0]), interpolation="linear"
    # )
    # seg_image = resize(
    #     seg_image, size=np.array([512, 512, 0]), interpolation="nearest"
    # )

    match setting:
        case 1:  # Crop to the bounding box of the mask
            bbox = RegionBox.from_mask_bbox(seg_image).expand_to_min_size(25)
            cropped_image = bbox.crop_image(ct_image)
            cropped_mask = bbox.crop_image(seg_image)
        case 2:  # Use the full image
            cropped_image = ct_image
            cropped_mask = seg_image

    new_size = 512
    if dim == 0:
        sz = Size3D(new_size, new_size, 0)
    elif dim == 1:
        sz = Size3D(new_size, 0, new_size)

    sz = Size3D(new_size, new_size, new_size)

    slices = SliceImage3D(
        image=cropped_image,
        mask=cropped_mask,
    )

    slices.generate_dim_slices(dim, every_n=every).view()


# %%
