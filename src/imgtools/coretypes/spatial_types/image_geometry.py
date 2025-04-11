from dataclasses import dataclass

from imgtools.coretypes.spatial_types import (
    Coordinate3D,
    Direction,
    Size3D,
    Spacing3D,
)


@dataclass(frozen=True)
class ImageGeometry:
    """Represents the geometry of a 3D image."""

    size: Size3D
    origin: Coordinate3D
    direction: Direction
    spacing: Spacing3D
