from pathlib import Path
from typing import NamedTuple

import SimpleITK as sitk
from rich.console import Console
from rich.table import Column, Table

from imgtools.coretypes.base_masks import ROIMaskMapping, VectorMask


def create_demo_vector_mask(
    size: tuple[int, int] = (128, 128),
) -> tuple[sitk.Image, dict[str, int]]:
    """
    Create a 4-component VectorUInt8 image with overlapping synthetic shapes.

    Returns
    -------
    sitk.Image
        - Component 0: Circle
        - Component 1: Square
        - Component 2: stripe
        - Component 3: clover pattern
    dict[str, int]
        Mapping from component name to index.
    """
    img_size = list(size)
    dtype = sitk.sitkUInt8

    # Blank masks
    circle = sitk.Image(img_size, dtype)
    square = sitk.Image(img_size, dtype)
    stripe = sitk.Image(img_size, dtype)
    clover = sitk.Image(img_size, dtype)

    # Draw circle: set pixels inside radius
    center = [s // 2 for s in img_size]
    radius = min(img_size) // 3
    for y in range(img_size[1]):
        for x in range(img_size[0]):
            if (x - center[0]) ** 2 + (y - center[1]) ** 2 < radius**2:
                circle[x, y] = 1

    # move centre up and right a little
    center[0] += 10
    center[1] -= 10

    # Draw square: centered and overlapping with circle
    offset = radius
    for y in range(center[1] - offset, center[1] + offset):
        for x in range(center[0] - offset, center[0] + offset):
            square[x, y] = 1

    # Draw stripe-ish diagonal stripe
    for i in range(img_size[0]):
        for j in range(img_size[1]):
            if abs(i - j) < 10:  # diagonal band
                stripe[i, j] = 1

    # Draw clover pattern in the bottom right quadrant
    clover_center = [3 * img_size[0] // 4, 3 * img_size[1] // 4]
    clover_radius_outer = min(img_size) // 5
    clover_radius_inner = min(img_size) // 10
    num_points = 5

    for y in range(img_size[1]):
        for x in range(img_size[0]):
            dx = x - clover_center[0]
            dy = y - clover_center[1]
            distance = (dx**2 + dy**2) ** 0.5

            if distance == 0:  # Avoid division by zero
                clover[x, y] = 1
                continue

            # Calculate angle in radians
            angle = abs(((dx / distance) * 0) + ((dy / distance) * 1))
            angle = angle % (2 * 3.14159 / num_points)

            # Threshold changes based on angle to create clover points
            threshold = clover_radius_inner + (
                clover_radius_outer - clover_radius_inner
            ) * abs(angle - 3.14159 / num_points) / (3.14159 / num_points)

            if distance < threshold:
                clover[x, y] = 1

    # Compose into a VectorUInt8 image
    vector_mask = sitk.Compose([circle, square, stripe, clover])

    mapping = {
        "circle": 0,
        "square": 1,
        "stripe": 2,
        "clover": 3,
    }
    return vector_mask, mapping


class PartitionResult(NamedTuple):
    label_image: sitk.Image
    lookup_table: dict[int, list[ROIMaskMapping]]


def collapse_vector_mask(
    vector_mask: VectorMask,
    separator: str = "+",
) -> PartitionResult:
    """
    Encodes a VectorUInt8 image (with binary 0/1 components) into a single-channel
    image where each voxel value is a unique integer representing the bitmask
    of active components. Names are used in the lookup table.

    Parameters
    ----------
    vector_mask : sitk.Image
        A VectorUInt8 image where each component is 0 or 1.

    component_names : dict[str, int]
        Mapping from name to index (e.g., {"circle": 0, "square": 1, "stripe": 2})

    separator : str
        String used to join names in the lookup table values.

    Returns
    -------
    PartitionResult
        - label_image: scalar UInt16 image of unique bitmask-encoded labels
        - lookup_table: dict[label_value] = joined component name string
    """
    n_components = vector_mask.GetNumberOfComponentsPerPixel()
    assert vector_mask.GetPixelID() == sitk.sitkVectorUInt8
    assert len(component_names) == n_components

    # Reverse the name map for easy index lookup
    index_to_roi_mapping: dict[int, ROIMaskMapping] = vector_mask.roi_mapping

    label_image = sitk.Image(vector_mask.GetSize(), sitk.sitkUInt16)
    label_image.CopyInformation(vector_mask)

    for i in range(n_components):
        component = sitk.VectorIndexSelectionCast(
            vector_mask, i, outputPixelType=sitk.sitkUInt16
        )
        shifted = sitk.ShiftScale(component, shift=0, scale=2**i)
        label_image += shifted

    max_val = 2**n_components
    lookup_table = {}

    for value in range(1, max_val):
        indices = [i for i in range(n_components) if (value >> i) & 1]
        # skip Bckround
        names = [index_to_roi_mapping[i + 1].image_id for i in indices]
        lookup_table[value] = names

    return PartitionResult(label_image=label_image, lookup_table=lookup_table)


if __name__ == "__main__":
    output_dir = Path(__file__).parent

    # --- Example usage
    img, component_names = create_demo_vector_mask()

    vm = VectorMask(
        image=img,
        roi_mapping={
            i: ROIMaskMapping(
                roi_key=name, roi_names=name, image_id=name.upper()
            )
            for name, i in component_names.items()
        },
        metadata={},
    )

    sitk.WriteImage(vm, output_dir / "vector_mask.nii.gz")
    result = collapse_vector_mask(vm, component_names)

    sitk.WriteImage(result.label_image, output_dir / "collapsed_mask.nii.gz")
    console = Console()

    component_names = list(component_names.keys())
    table = Table(
        Column("Value", justify="right", style="cyan", no_wrap=True),
        *[
            Column(name.upper(), justify="center", style="magenta")
            for name in component_names
        ],
        title="Component Presence Matrix",
    )

    for value in sorted(result.lookup_table.keys()):
        present = set(result.lookup_table[value])
        row = [str(value)] + [
            "✔" if name.upper() in present else "" for name in component_names
        ]
        table.add_row(*row)

    console.print(table)
