from typing import Any, Dict

import SimpleITK as sitk


class Scan(sitk.Image):
    metadata: Dict[str, str]

    def __init__(self, image: sitk.Image, metadata: Dict[str, str]) -> None:
        self.image = image
        self.metadata = metadata

    def __getitem__(self, idx) -> Any:  # noqa
        if isinstance(idx, str):
            if idx == "origin":
                return self.GetOrigin()
            elif idx == "spacing":
                return self.GetSpacing()
            elif idx == "direction":
                return self.GetDirection()

        return super().__getitem__(idx)
