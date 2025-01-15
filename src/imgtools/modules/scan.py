from typing import Dict, TypeVar

import SimpleITK as sitk

T = TypeVar("T")


class Scan:
    def __init__(self, image: sitk.Image, metadata: Dict[str, T]) -> None:
        self.image = image
        self.metadata = metadata
