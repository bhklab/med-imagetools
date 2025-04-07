from __future__ import annotations

from typing import TYPE_CHECKING, Dict

from imgtools.coretypes.imagetypes import MedImage
from imgtools.io.readers import read_dicom_series

if TYPE_CHECKING:
    import SimpleITK as sitk

__all__ = ["Scan"]


def read_dicom_scan(
    path: str,
    series_id: list[str] | None = None,
    recursive: bool = False,
    file_names: list[str] | None = None,
) -> Scan:
    image = read_dicom_series(
        path,
        series_id=series_id,
        recursive=recursive,
        file_names=file_names,
    )
    return Scan(image, {})


class Scan(MedImage):
    metadata: Dict[str, str]

    def __init__(self, image: sitk.Image, metadata: Dict[str, str]) -> None:
        super().__init__(image)
        self.metadata = metadata

    def __repr__(self) -> str:  # type: ignore
        # convert metadata and img_stats to string
        # with angulated brackets
        retr_str = "Scan<"
        for k, v in self.metadata.items():
            retr_str += f"\n\t{k}={v}"
        for k, v in self.img_stats.items():
            retr_str += f"\n\t{k}={v}"
        retr_str += "\n>"
        return retr_str


if __name__ == "__main__":
    directory = "data/4D-Lung/113_HM10395/CT_Series00173972"
    scan = read_dicom_scan(directory)
    print(f"{scan!r}")
