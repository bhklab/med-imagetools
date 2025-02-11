from typing import Dict, TypeVar

import SimpleITK as sitk


class Scan(sitk.Image):
    metadata: Dict[str, str]

    def __init__(self, image: sitk.Image, metadata: Dict[str, str]) -> None:
        self.image = image
        self.metadata = metadata
