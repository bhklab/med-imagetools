import SimpleITK as sitk
from typing import Dict, TypeVar

T = TypeVar('T')

class Scan:
    def __init__(self, image: sitk.Image, metadata: Dict[str, T]):
        self.image = image
        self.metadata = metadata