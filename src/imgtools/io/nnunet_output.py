from __future__ import annotations

import contextlib
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Sequence

import pandas as pd
from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    field_validator,
)

from imgtools.coretypes import MedImage, VectorMask
from imgtools.io.validators import validate_directory
from imgtools.io.writers import (
    AbstractBaseWriter,
    ExistingFileMode,
    NIFTIWriter,
)
from imgtools.loggers import logger
from imgtools.utils.nnunet import (
    MODALITY_MAP,
    generate_dataset_json,
    generate_nnunet_scripts,
)

__all__ = ["nnUNetOutput"]


class MaskSavingStrategy(str, Enum):
    """
    Enum for mask saving strategies.

    Attributes
    ----------
    LABEL_IMAGE : str
        No overlaps allowed.
    SPARSE_MASK : str
        Allows overlaps, but is lossy due to argmax.
    REGION_MASK : str
        Work around that creates a new region for each overlap.
    """

    LABEL_IMAGE = "label_image"
    SPARSE_MASK = "sparse_mask"
    REGION_MASK = "region_mask"


class nnUNetOutput(BaseModel):  # noqa: N801
    """
    Configuration model for saving medical imaging outputs in nnUNet format.

    This class provides a standardized configuration for saving medical images,
    supporting various file formats and output organization strategies.

    Attributes
    ----------
    directory : Path
        Directory where output files will be saved. Must exist and be writable.
    filename_format : str
        Format string for output filenames with placeholders for metadata values.
    existing_file_mode : ExistingFileMode
        How to handle existing files (FAIL, SKIP, OVERWRITE).
    extra_context : Dict[str, Any]
        Additional metadata to include when saving files.

    Examples
    --------
    >>> from imgtools.io import nnUNetOutput
    >>> from imgtools.io.writers import ExistingFileMode
    >>> output = nnUNetOutput(
    ...     directory="results/patient_scans",
    ...     existing_file_mode=ExistingFileMode.SKIP,
    ... )
    >>> output(scan_list)  # Save all scans in the list
    """

    directory: Path = Field(
        description="Path where output files will be saved. Absolute path or relative to the current working directory.",
        title="Output Directory",
        examples=["output/processed_scans", "/absolute/path/to/output"],
    )
    dataset_name: str = Field(
        description="Name of the dataset being processed.",
        title="Dataset Name",
        examples=["NSCLC-Radiomics"],
    )
    roi_keys: list[str] = Field(
        description="List of ROI's to process.",
        title="ROI Keys",
        examples=["Lung_L", "Lung_R"],
    )
    mask_saving_strategy: MaskSavingStrategy = Field(
        MaskSavingStrategy.LABEL_IMAGE,
        description="Strategy for saving masks: 'label_image' for no overlap, 'sparse_mask' for lossy, or 'region_mask'.",
        title="Mask Saving Strategy",
        examples=["label_image", "sparse_mask", "region_mask"],
    )
    existing_file_mode: ExistingFileMode = Field(
        ExistingFileMode.FAIL,
        description="How to handle existing files: FAIL (raise error), SKIP (don't overwrite), or OVERWRITE (replace existing files).",
        title="Existing File Handling",
    )
    extra_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata fields to include when saving files. These values can be referenced in the filename_format.",
        title="Extra Metadata",
        examples=[
            {"dataset": "NSCLC-Radiomics", "processing_date": "2025-04-22"}
        ],
    )

    dataset_id: int = Field(init=False, default=1)

    _writer: AbstractBaseWriter | None = PrivateAttr(default=None)
    _file_name_format: str | None = PrivateAttr(default=None)

    def model_post_init(self, __context) -> None:  # type: ignore # noqa: ANN001
        """Initialize the writer after model initialization."""
        # Create required directories
        for subdir in ["nnUNet_results", "nnUNet_preprocessed", "nnUNet_raw"]:
            (self.directory / subdir).mkdir(parents=True, exist_ok=True)

        # Determine the next available dataset ID
        existing_ids = {
            int(folder.name[7:10])
            for folder in (self.directory / "nnUNet_raw").glob("Dataset*")
            if folder.name[7:10].isdigit()
        }
        self.dataset_id = min(set(range(1, 1000)) - existing_ids)

        # Update root directory to the specific dataset folder
        self.directory = (
            self.directory
            / "nnUNet_raw"
            / f"Dataset{self.dataset_id:03d}_{self.dataset_name}"
        )

        self._file_name_format = (
            "{DirType}{SplitType}/{Dataset}_{SampleID}.nii.gz"
        )

        self._writer = NIFTIWriter(
            root_directory=self.directory,
            existing_file_mode=self.existing_file_mode,
            filename_format=self._file_name_format,
            context=self.extra_context,
        )

    @field_validator("directory")
    @classmethod
    def validate_directory(cls, v: str | Path) -> Path:
        """Validate that the output directory exists or can be created, and is writable."""
        return validate_directory(v)

    @classmethod
    def default(cls) -> nnUNetOutput:
        """Create a default instance of SampleOutput."""
        return cls(
            directory=Path("output"),
            dataset_name="Dataset",
            roi_keys=["ROI_1", "ROI_2"],
            existing_file_mode=ExistingFileMode.FAIL,
            extra_context={},
        )

    @property
    def writer(self) -> AbstractBaseWriter:
        """Get the writer instance."""
        if self._writer is None:
            raise ValueError("Writer is not initialized.")
        return self._writer

    def finalize_dataset(self) -> None:
        """Finalize dataset by generating preprocessing scripts and dataset JSON configuration."""

        generate_nnunet_scripts(self.directory, self.dataset_id)

        index_df = pd.read_csv(self.writer.index_file)
        _image_modalities = index_df["Modality"].unique()

        # Construct channel names mapping
        channel_names = {
            channel_num.lstrip("0") or "0": modality
            for modality, channel_num in MODALITY_MAP.items()
            if modality in _image_modalities
        }

        # Count the number of training cases
        num_training_cases = sum(
            1
            for file in (self.directory / "imagesTr").iterdir()
            if file.is_file()
        )

        # Construct labels
        labels = {"background": 0}
        if self.mask_saving_strategy == "region_mask":
            n_components = len(self.roi_keys)
            max_val = 2**n_components

            for component_index in range(n_components):
                indices = [
                    value
                    for value in range(1, max_val)
                    if (value >> component_index) & 1
                ]
                labels[self.roi_keys[component_index]] = indices
            regions_class_order = [idx + 1 for idx in range(n_components)]
        else:
            labels = {
                **{label: i + 1 for i, label in enumerate(self.roi_keys)},
            }
            regions_class_order = None

        generate_dataset_json(
            self.directory,
            channel_names=channel_names,
            labels=labels,
            num_training_cases=num_training_cases,
            file_ending=".nii.gz",
            regions_class_order=regions_class_order,
        )

    def __call__(
        self,
        data: Sequence[MedImage],
        /,
        SampleNumber: str,
        **kwargs: object,  # noqa: N803
    ) -> Sequence[Path]:
        """
        Save the data to files using the configured writer.

        Parameters
        ----------
        data : List[MedImage]
            List of medical images to save.
        **kwargs
            Additional metadata to include when saving.

        Returns
        -------
        List[Path]
            List of paths to the saved files.
        """

        if not any(isinstance(image, VectorMask) for image in data):
            # Usually happens when none of the roi names match
            msg = f"No segmentation images found in sample {SampleNumber}"
            raise ValueError(msg)

        for image in data:
            if isinstance(image, VectorMask) and not all(
                roi_key in image.roi_keys for roi_key in self.roi_keys
            ):
                msg = f"Not all required roi names found in sample {SampleNumber}. Expected: {self.roi_keys}. Found: {image.roi_keys}"
                raise ValueError(msg)

        saved_files = []
        for image in data:
            if isinstance(image, VectorMask):
                match self.mask_saving_strategy:
                    case MaskSavingStrategy.LABEL_IMAGE:
                        mask = image.to_label_image()
                    case MaskSavingStrategy.SPARSE_MASK:
                        mask = image.to_sparse_mask()
                    case MaskSavingStrategy.REGION_MASK:
                        mask = image.to_region_mask()
                    case _:
                        msg = f"Unknown mask saving strategy: {self.mask_saving_strategy}"
                        raise ValueError(msg)

                p = self.writer.save(
                    mask,
                    DirType="labels",
                    SplitType="Tr",
                    SampleID=SampleNumber,
                    Dataset=self.dataset_name,
                    **image.metadata,
                    **kwargs,
                )
                saved_files.append(p)

            elif isinstance(image, MedImage):
                # Handle MedImage case
                p = self.writer.save(
                    image,
                    DirType="images",
                    SplitType="Tr",
                    SampleID=f"{SampleNumber}_{MODALITY_MAP[image.metadata['Modality']]}",
                    Dataset=self.dataset_name,
                    **image.metadata,
                    **kwargs,
                )
                saved_files.append(p)
            else:
                errmsg = (
                    f"Unsupported image type: {type(image)}. "
                    "Expected MedImage or VectorMask."
                )
                logger.error(errmsg)
                raise TypeError(errmsg)
        return saved_files


if __name__ == "__main__":
    from imgtools.io.sample_input import SampleInput

    input_directory = "./data/RADCURE"
    output_directory = Path("./temp_outputs")
    output_directory.mkdir(exist_ok=True)
    modalities = ["CT", "RTSTRUCT"]
    roi_match_map = {
        "BRAIN": ["Brain"],
        "BRAINSTEM": ["Brainstem"],
    }

    input = SampleInput.build(  # noqa: A001
        directory=Path(input_directory),
        modalities=modalities,
        roi_match_map=roi_match_map,
    )
    output = nnUNetOutput(
        directory=output_directory,
        existing_file_mode=ExistingFileMode.OVERWRITE,
        dataset_name="RADCURE",
        extra_context={},
        roi_keys=list(roi_match_map.keys()),
        mask_saving_strategy=MaskSavingStrategy.REGION_MASK,
    )

    samples = input.query()

    for idx, sample in enumerate(samples, start=1):
        loaded_sample = input(sample)

        with contextlib.suppress(Exception):
            output(loaded_sample, SampleNumber=f"{idx:03}")

        if idx == 5:
            break

    output.finalize_dataset()
