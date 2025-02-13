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

    def __repr__(self) -> str:  # type: ignore
        # convert metadata and img_stats to string
        # with angulated brackets
        metadata = "\n\t".join([f"{k}={v}" for k, v in self.metadata.items()])
        img_stats = "\n\t".join(
            [f"{k}={v}" for k, v in self._img_stats.items()]
        )
        return f"Scan<\n{metadata}, {img_stats}\n>"

    def __rich_repr__(self) -> Generator[tuple[str, str], Any, None]:
        for k, v in self.metadata.items():
            yield k, v
        for k, v in self._img_stats.items():
            yield k, v

    @property
    def image(self) -> sitk.Image:
        """This is for backward compatibility."""
        return self
