from typing import Any, Dict, Generator

import SimpleITK as sitk


class Scan(sitk.Image):
    def __init__(self, image: sitk.Image, metadata: Dict[str, str]) -> None:
        super().__init__(image)
        self.metadata = metadata

    @property
    def _img_stats(self) -> Dict[str, str]:
        stats = {}
        stats["size"] = self.GetSize()
        stats["spacing"] = self.GetSpacing()
        stats["origin"] = self.GetOrigin()
        stats["direction"] = self.GetDirection()
        return stats

    def __rich_repr__(self) -> Generator[tuple[str, str], Any, None]:
        for k, v in self.metadata.items():
            yield k, v
        for k, v in self._img_stats.items():
            yield k, v
