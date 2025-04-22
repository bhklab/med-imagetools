from pathlib import Path
from typing import NamedTuple

import SimpleITK as sitk
from rich import print  # noqa: A004


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
        - Component 2: Triangle-like diagonal stripe
        - Component 3: Star pattern
    dict[str, int]
        Mapping from component name to index.
    """
    img_size = list(size)
    dtype = sitk.sitkUInt8

    # Blank masks
    circle = sitk.Image(img_size, dtype)
    square = sitk.Image(img_size, dtype)
    triangle = sitk.Image(img_size, dtype)
    star = sitk.Image(img_size, dtype)

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

    # Draw triangle-ish diagonal stripe
    for i in range(img_size[0]):
        for j in range(img_size[1]):
            if abs(i - j) < 10:  # diagonal band
                triangle[i, j] = 1

    # Draw star pattern in the bottom right quadrant
    star_center = [3 * img_size[0] // 4, 3 * img_size[1] // 4]
    star_radius_outer = min(img_size) // 5
    star_radius_inner = min(img_size) // 10
    num_points = 5

    for y in range(img_size[1]):
        for x in range(img_size[0]):
            dx = x - star_center[0]
            dy = y - star_center[1]
            distance = (dx**2 + dy**2) ** 0.5

            if distance == 0:  # Avoid division by zero
                star[x, y] = 1
                continue

            # Calculate angle in radians
            angle = abs(((dx / distance) * 0) + ((dy / distance) * 1))
            angle = angle % (2 * 3.14159 / num_points)

            # Threshold changes based on angle to create star points
            threshold = star_radius_inner + (
                star_radius_outer - star_radius_inner
            ) * abs(angle - 3.14159 / num_points) / (3.14159 / num_points)

            if distance < threshold:
                star[x, y] = 1

    # Compose into a VectorUInt8 image
    vector_mask = sitk.Compose([circle, square, triangle, star])

    mapping = {
        "circle": 0,
        "square": 1,
        "triangle": 2,
        "star": 3,
    }
    return vector_mask, mapping


class PartitionResult(NamedTuple):
    label_image: sitk.Image
    lookup_table: dict[int, str]


def collapse_vector_mask(
    vector_mask: sitk.Image,
    component_names: dict[str, int],
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
        Mapping from name to index (e.g., {"circle": 0, "square": 1, "triangle": 2})

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
    index_to_name = {v: k for k, v in component_names.items()}

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
        names = [index_to_name[i] for i in indices]
        lookup_table[value] = separator.join(names)

    return PartitionResult(label_image=label_image, lookup_table=lookup_table)


if __name__ == "__main__":
    output_dir = Path(__file__).parent

    # --- Example usage
    vm, component_names = create_demo_vector_mask()

    sitk.WriteImage(vm, output_dir / "vector_mask.nii.gz")
    result = collapse_vector_mask(vm, component_names)

    sitk.WriteImage(result.label_image, output_dir / "collapsed_mask.nii.gz")
    print(result.lookup_table)
