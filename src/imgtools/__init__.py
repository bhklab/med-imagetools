__version__ = "1.18.0"
from .coretypes import Coordinate3D, Size3D, Spacing3D, Vector3D
from .datasets import example_data
from .dicom import find_dicoms, lookup_tag, similar_tags, tag_exists
from .logging import logger

__all__ = [
    "find_dicoms",
    "lookup_tag",
    "similar_tags",
    "tag_exists",
    "logger",
    ## coretypes
    "Coordinate3D",
    "Size3D",
    "Spacing3D",
    "Vector3D",
    "example_data",
]
