from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from imgtools.coretypes.base_masks import VectorMask
from imgtools.coretypes.base_medimage import MedImage
from imgtools.coretypes.imagetypes.scan import Scan
from imgtools.io.writers import (
    AbstractBaseWriter,
    ExistingFileMode,
    NIFTIWriter,
)

DEFAULT_FILENAME_FORMAT = (
    "{PatientID}/{Modality}_{trunc_SeriesInstanceUID}/{ImageID}.nii.gz"
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
                        matched_rois_str = "|".join(matched_rois)
                        image_id = f"{roi_key}_[{matched_rois_str}]"
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
                        **image.metadata,
                        **kwargs,
                        trunc_SeriesInstanceUID=image.metadata[
                            "SeriesInstanceUID"
                        ][-8:],
                        ImageID=image.metadata["Modality"],
                    )

                case _:
                    print(
                        f"Unsupported data type: {type(image)}. Only VectorMask is supported."
                    )
                    pass

        return {}
