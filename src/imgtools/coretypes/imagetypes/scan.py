from typing import Dict

import SimpleITK as sitk

from imgtools.coretypes.imagetypes import MedImage

__all__ = ["Scan"]


class Scan(MedImage):
    metadata: Dict[str, str]

    def __init__(self, image: sitk.Image, metadata: Dict[str, str]) -> None:
        super().__init__(image)
        self.metadata = metadata

    def __repr__(self) -> str:  # type: ignore
        # convert metadata and img_stats to string
        # with angulated brackets
        metadata = "\n\t".join(
            sorted([f"{k}={v}" for k, v in self.metadata.items()])
        )
        img_stats = "\n\t".join(
            [f"{k}={v}" for k, v in self.img_stats.items()]
        )
        return f"Scan<\n\t{metadata}, {img_stats}\n>"
