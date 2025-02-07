from typing import Dict, TypeVar

import SimpleITK as sitk

T = TypeVar("T")


class Scan(sitk.Image):
    def __init__(self, image: sitk.Image, metadata: Dict[str, T]) -> None:
        super().__init__(image)
        self.metadata = metadata
