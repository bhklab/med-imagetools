"""3DSliceImages: Efficiently generate and store 2D slices from a 3D SimpleITK image."""

# %%
"""3DSliceImages: Efficiently generate and store 2D slices from a 3D SimpleITK image."""

from dataclasses import dataclass, field
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import SimpleITK as sitk
from IPython.display import display
from PIL import Image

from imgtools import Size3D
from imgtools.ops import Resize
from imgtools.utils import image_to_array


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


def _generate_slice(
    index: int, array: np.ndarray, cmap: str, dpi: int
) -> tuple[int, np.ndarray]:
    """Generate a single 2D slice."""
    # Create a new figure and axis with the specified DPI
    fig, ax = plt.subplots()

    # Display the array as an image with the specified colormap
    ax.imshow(array, cmap=cmap, origin="lower")

    # Remove the axis for a cleaner image
    # ax.axis("off")

    # Draw the canvas to update the figure
    fig.canvas.draw()

    # Convert the canvas to a numpy array
    image = np.frombuffer(fig.canvas.tostring_argb(), dtype=np.uint8)

    # Reshape the array to match the canvas dimensions and remove the alpha channel
    image = image.reshape(fig.canvas.get_width_height()[::-1] + (4,))
    image = image[..., 1:]  # Remove the alpha channel

    # Close the figure to free up memory
    plt.close(fig)

    return index, Image.fromarray(image, mode="RGB")


@dataclass
class SliceImage3D:
    """Generates 2D slices from a 3D SimpleITK image across all three dimensions."""

    image: sitk.Image
    num_processors: int = field(default_factory=cpu_count)
    resizer_interpolation: str = field(
        default="linear", metadata={"choices": ["linear", "nearest"]}
    )
    cmap: str = "gray"
    dpi: int = 100

    slices: ImageSlices = field(init=False)
    origin: tuple[float, float, float] = field(init=False)
    direction: tuple[float, float, float] = field(init=False)
    spacing: tuple[float, float, float] = field(init=False)
    cropped_size: Size3D = field(default_factory=lambda: Size3D(256, 256, 0))

    def __post_init__(self) -> None:
        # Convert image once instead of multiple times
        match self.resizer_interpolation:
            case "linear":
                resizer = Resize(
                    list(self.cropped_size), interpolation="linear"
                )
            case "nearest":
                resizer = Resize(
                    list(self.cropped_size), interpolation="nearest"
                )
        image = resizer(self.image)
        self.image_array, self.origin, self.direction, self.spacing = (
            image_to_array(image)
        )

    def generate_dim_slices(self, dim: int) -> None:
        """Generate all slices efficiently using multiprocessing."""
        # if dim == 0:
        #     slices = [
        #         self.image_array[i, :, :]
        #         for i in range(self.image_array.shape[0])
        #     ]
        # elif dim == 1:
        #     slices = [
        #         self.image_array[:, i, :]
        #         for i in range(self.image_array.shape[1])
        #     ]
        # else:
        #     slices = [
        #         self.image_array[:, :, i]
        #         for i in range(self.image_array.shape[2])
        #     ]
        slices = [
            np.take(self.image_array, i, axis=dim)
            for i in range(self.image_array.shape[dim])
        ]

        tasks = [(i, slc, self.cmap, self.dpi) for i, slc in enumerate(slices)]

        # display progress bar with tqdm_notebook
        results = [_generate_slice(*task) for task in tqdm(tasks)]

        # Store slices in a dictionary (key: (dimension, index))
        images = {(dim, index): image for index, image in results}
        self.slices = ImageSlices.from_dict(images)

    def __repr__(self) -> str:
        slices_by_dimension = {
            dim: sum(1 for key in self.slices if key[0] == dim)
            for dim in range(3)
        }
        return (
            f"SliceImage3D(image_shape={self.image_array.shape}, "
            f"origin={self.origin}, direction={self.direction}, "
            f"spacing={self.spacing}, "
            f"slices_by_dimension={slices_by_dimension})"
        )


# %%
from rich import print, progress  # type: ignore # noqa

# Load example images
ct_image = sitk.ReadImage(
    "/home/bioinf/bhklab/radiomics/readii-negative-controls/rawdata/RADCURE/images/niftis/SubjectID-3_RADCURE-4106/CT_70181_original.nii.gz"
)
seg_image = sitk.ReadImage(
    "/home/bioinf/bhklab/radiomics/readii-negative-controls/rawdata/RADCURE/images/niftis/SubjectID-3_RADCURE-4106/RTSTRUCT_54305_GTV.nii.gz"
)

slices = SliceImage3D(ct_image, num_processors=4)

# %%
dim = 0

slices.generate_dim_slices(dim)

print(slices)

# %%
# get a slice
img = slices.slices[1]

display(img)


print(slices.image_array[9, :, :].nbytes)

# %%
# display it
plt.imshow(img)
plt.show()

# %%
