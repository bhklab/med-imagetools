from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich import print

from imgtools.coretypes.base_masks import VectorMask
from imgtools.coretypes.base_medimage import MedImage
from imgtools.coretypes.imagetypes.scan import Scan
from imgtools.io.writers import (
    AbstractBaseWriter,
    ExistingFileMode,
    NIFTIWriter,
)
from imgtools.utils import sanitize_file_name

DEFAULT_FILENAME_FORMAT = (
    "{PatientID}/{Modality}_Series-{trunc_SeriesInstanceUID}/{ImageID}.nii.gz"
)


@dataclass
class SampleOutput:
    directory: Path
    filename_format: str = field(default=DEFAULT_FILENAME_FORMAT)

    writer: AbstractBaseWriter = field(
        init=False,
    )

    def __post_init__(self) -> None:
        self.writer = NIFTIWriter(
            root_directory=self.directory,
            existing_file_mode=ExistingFileMode.FAIL,
            filename_format=self.filename_format,
        )

    def __call__(
        self, data: list[MedImage], **kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Save the data to a file using the writer.

        Args:
            data (Any): The data to be saved.
            name (str): The name of the file.
            index (int, optional): The index of the file. Defaults to 0.
            extension (str, optional): The file extension. Defaults to ".nii".
        """
        for image in data:
            match image:
                case VectorMask(roi_mapping, metadata):
                    for label, (roi_key, matched_rois) in roi_mapping.items():
                        if label == 0:
                            continue  # Skip background
                        roi_mask = image.extract_mask(label)
                        image_id = f"{label:02}-{roi_key}"
                        self.writer.save(
                            roi_mask,
                            roi_key=roi_key,
                            matched_rois=matched_rois,
                            trunc_SeriesInstanceUID=metadata[
                                "SeriesInstanceUID"
                            ][-8:],
                            **metadata,
                            **kwargs,
                            ImageID=image_id,
                        )
                case Scan():
                    # Handle MedImage cae
                    self.writer.save(
                        image,
                        **kwargs,
                        trunc_SeriesInstanceUID=image.metadata[
                            "SeriesInstanceUID"
                        ][-8:],
                        ImageID=image.metadata["Modality"],
                        **image.metadata,
                    )

                case _:
                    print(
                        f"Unsupported data type: {type(image)}. Only VectorMask is supported."
                    )
                    pass

        return {}
