from typing import Dict, TypeVar

import SimpleITK as sitk

T = TypeVar("T")


class Scan:
    def __init__(self, image: sitk.Image, metadata: Dict[str, T]) -> None:
        self.image = image
        self.metadata = metadata

        self.metadata.update(self._getimgmetadata())

    def _getimgmetadata(self):
        size = self.image.GetSize()
        spacing = self.image.GetSpacing()
        origin = self.image.GetOrigin()
        direction = self.image.GetDirection()

        statisticsfilter = sitk.StatisticsImageFilter()

        statisticsfilter.Execute(self.image)

        return {
            "size": size,
            "spacing": spacing,
            "origin": origin,
            "direction": direction,
            "min": statisticsfilter.GetMinimum(),
            "max": statisticsfilter.GetMaximum(),
            "mean": statisticsfilter.GetMean(),
            "std": statisticsfilter.GetSigma(),
        }

    def __repr__(self) -> str:  # type: ignore
        # return f"Scan(metadata={self.metadata})"
        metadata_str = "\n\t".join(
            [f"{k}: {v}" for k, v in self.metadata.items()]
        )

        return f"Scan(\n\t{metadata_str}\n)"
