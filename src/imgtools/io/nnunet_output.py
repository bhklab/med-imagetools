from __future__ import annotations

import contextlib
from enum import Enum
from math import ceil
from pathlib import Path
import random
from shutil import move
from typing import Any, Dict, Sequence,List

import pandas as pd
from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    field_validator,
)

from imgtools.autopipeline import ProcessSampleResult
from imgtools.coretypes import MedImage, Scan, VectorMask
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

__all__ = ["nnUNetOutput", "MaskSavingStrategy"]


class nnUNetOutputError(Exception):  # noqa: N801
    """Base class for errors related to sample data."""

    pass


class NoSegmentationImagesError(nnUNetOutputError):
    """Raised when no segmentation images are found in a sample."""

    def __init__(self, sample_number: str) -> None:
        msg = f"No segmentation images found in sample {sample_number}"
        super().__init__(msg)
        self.sample_number = sample_number


class MissingROIsError(nnUNetOutputError):
    """Raised when a VectorMask does not contain all required ROI keys."""

    def __init__(
        self,
        sample_number: str,
        expected_rois: list[str],
        found_rois: list[list[str]],
    ) -> None:
        msg = (
            f"Not all required ROI names found in sample {sample_number}. "
            f"Expected: {expected_rois}. Found: {found_rois}"
        )
        super().__init__(msg)
        self.sample_number = sample_number
        self.expected_rois = expected_rois
        self.found_rois = found_rois


class MaskSavingStrategy(str, Enum):
    """
    Enum for mask saving strategies.

    Attributes
    ----------
    LABEL_IMAGE : str
        No overlaps allowed.
    SPARSE_MASK : str
        Allows overlaps, but is lossy if overlaps exist.
    REGION_MASK : str
        Work around that creates a new region for each overlap.
    """

    LABEL_IMAGE = "label_image"
    SPARSE_MASK = "sparse_mask"
    REGION_MASK = "region_mask"


class MaskSavingStrategyError(nnUNetOutputError):
    """Raised when an invalid mask saving strategy is provided."""


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
        ExistingFileMode.OVERWRITE,
        description="How to handle existing files: FAIL (raise error), SKIP (don't overwrite), or OVERWRITE (replace existing files).",
        title="Existing File Handling",
    )
    test_set_ratio: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "Proportion of successfully processed cases assigned to the test set "
            "(imagesTs/labelsTs). The count is ceil(ratio * n_cases); use 1.0 for a "
            "full test set (imagesTr will be empty and numTraining will be 0)."
        ),
        title="Test Set Ratio",
    )
    random_seed: int = Field(
        default=42,
        description="The random seed to use for the test set split.",
        title="Random Seed",
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
            "{DirType}{SplitType}/{PatientID}_{SampleID}.nii.gz"
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
            mask_saving_strategy=MaskSavingStrategy.LABEL_IMAGE,
            existing_file_mode=ExistingFileMode.FAIL,
            extra_context={},
        )

    @property
    def writer(self) -> AbstractBaseWriter:
        """Get the writer instance."""
        if self._writer is None:
            raise ValueError("Writer is not initialized.")
        return self._writer

    def _get_valid_masks(
        self,
        data: Sequence[MedImage],
        SampleNumber: str,  # noqa: N803
    ) -> list[VectorMask]:
        """
        Get the valid VectorMask instances from the data.

        A valid VectorMask is one that contains all required ROI keys.

        Parameters
        ----------
        data : List[MedImage]
            List of medical images to search for valid VectorMasks.
        SampleNumber : str
            The sample number for error reporting.

        Returns
        -------
        List[VectorMask]
            List of valid VectorMask instances.
        """
        if not any(isinstance(image, VectorMask) for image in data):
            raise NoSegmentationImagesError(SampleNumber)

        valid_masks: list[VectorMask] = []

        for image in data:
            if isinstance(image, VectorMask) and all(
                roi_key in image.roi_keys for roi_key in self.roi_keys
            ):
                valid_masks.append(image)

        if not valid_masks:
            raise MissingROIsError(
                SampleNumber,
                self.roi_keys,
                [img.roi_keys for img in data if isinstance(img, VectorMask)],
            )

        if len(valid_masks) > 1:
            logger.warning(
                "Multiple valid segmentations found in sample %s. Picking the first one.",
                SampleNumber,
            )

        return valid_masks
    
    def _move_file_to_test_split(self, file_path: Path, dir_map: dict[str, str]) -> Path:
        """
        Calculates the Ts path and moves the file based on the provided directory map.
        Parameters
        ----------
        file_path: Path
            The path to the file that is to be moved
        dir_map: dict[str, str]
            A dictionary whose keys are the name of the source dir, and values are the names of the target dirs

        Returns
        -------
        Path
            The path where the file was moved.
        """

        if file_path.parent.name not in dir_map:
            raise ValueError(f"Unexpected parent directory for split: {file_path.parent.name}")

        # NOTE: nnUNet requires everything in images type dir to be a file.
        output_folder_path = file_path.parent.parent / dir_map[file_path.parent.name]
        target_path = output_folder_path / file_path.name
        output_folder_path.mkdir(exist_ok=True, parents=True)
        move(file_path, target_path)
        return target_path

    def _patch_index_for_test_split(self, moved_sample_ids: set[str]) -> None:
        """Update index rows for cases moved to imagesTs/labelsTs.

        Assumes filepath values are relative to the dataset root with the split
        directory as the first path component (e.g. ``imagesTr/case_0001.nii.gz``).
        """
        index_file = self.writer.index_file
        if not moved_sample_ids or not index_file.exists():
            return

        dir_map = {"imagesTr": "imagesTs", "labelsTr": "labelsTs"}
        df = pd.read_csv(index_file, dtype={"SampleID": str})

        def belongs_to_moved_case(sample_id: str) -> bool:
            sample_id = str(sample_id)
            return any(
                sample_id == mid or sample_id.startswith(f"{mid}_")
                for mid in moved_sample_ids
            )

        def rewrite_split_path(filepath: str) -> str:
            parts = Path(filepath).parts
            if not parts or parts[0] not in dir_map:
                return filepath
            return str(Path(dir_map[parts[0]], *parts[1:]))

        mask = df["SampleID"].map(belongs_to_moved_case)
        df.loc[mask, "filepath"] = df.loc[mask, "filepath"].map(rewrite_split_path)
        if "SplitType" in df.columns:
            df.loc[mask, "SplitType"] = "Ts"

        df.to_csv(index_file, index=False)

    def split_dataset(
        self,
        successful_results: List[ProcessSampleResult],
    ) -> None:
        """
        Split successfully processed cases into nnUNet train and test folders.

        Files must already be under imagesTr and labelsTr. Selected cases are moved
        to imagesTs and labelsTs. The number of test cases is
        ``ceil(test_set_ratio * n_cases)``. A ratio of 1.0 moves every case to the
        test set.

        Parameters
        ----------
        successful_results: List[ProcessSampleResult]
            Results for successfully processed cases.

        """
        if self.test_set_ratio == 0.0 or not successful_results:
            return

        n_cases = len(successful_results)
        n_test = ceil(self.test_set_ratio * n_cases)
        dir_map = {"labelsTr": "labelsTs", "imagesTr": "imagesTs"}

        pool = sorted(successful_results, key=lambda r: r.sample_id)
        rng = random.Random(self.random_seed)
        test_set = rng.sample(pool, n_test)

        for sample in test_set:
            sample.output_files = [
                self._move_file_to_test_split(path, dir_map)
                for path in sample.output_files
            ]

        self._patch_index_for_test_split({s.sample_id for s in test_set})

        logger.info(
            "Test set split: moved %d of %d cases to imagesTs/labelsTs "
            "(ratio=%.2f, seed=%d)",
            n_test,
            n_cases,
            self.test_set_ratio,
            self.random_seed,
        )
        if n_test == n_cases:
            logger.warning(
                "All %d successful cases were moved to the test set; "
                "imagesTr will be empty and numTraining will be 0.",
                n_cases,
            )

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
        labels: dict[str, int | list[int]] = {"background": 0}
        if self.mask_saving_strategy is MaskSavingStrategy.REGION_MASK:
            n_components = len(self.roi_keys)
            max_val = 2**n_components

            for component_index in range(n_components):
                indices = [
                    value
                    for value in range(1, max_val)
                    if (value >> component_index) & 1
                ]
                labels[self.roi_keys[component_index]] = indices
            regions_class_order = tuple(idx + 1 for idx in range(n_components))
        else:
            labels.update(
                {label: i + 1 for i, label in enumerate(self.roi_keys)}
            )
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
        SampleNumber: str,  # noqa: N803
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

        valid_masks = self._get_valid_masks(data, SampleNumber)
        selected_mask = valid_masks[0]  # Select the first valid mask

        saved_files = []

        match self.mask_saving_strategy:
            case MaskSavingStrategy.LABEL_IMAGE:
                mask = selected_mask.to_label_image()
            case MaskSavingStrategy.SPARSE_MASK:
                mask = selected_mask.to_sparse_mask()
            case MaskSavingStrategy.REGION_MASK:
                mask = selected_mask.to_region_mask()
            case _:
                msg = f"Unknown mask saving strategy: {self.mask_saving_strategy}"
                raise MaskSavingStrategyError(msg)

        roi_match_data = {
            f"roi_matches.{rmap.roi_key}": "|".join(rmap.roi_names)
            for rmap in selected_mask.roi_mapping.values()
        }

        p = self.writer.save(
            mask,
            DirType="labels",
            SplitType="Tr",
            SampleID=SampleNumber,
            Dataset=self.dataset_name,
            **roi_match_data,
            **selected_mask.metadata,
            **kwargs,
        )
        saved_files.append(p)

        for image in data:
            if isinstance(image, Scan):
                # Handle Scan case(CT or MR)
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
            elif isinstance(image, VectorMask):
                pass
            else:
                errmsg = (
                    f"Unsupported image type: {type(image)}. "
                    "Expected Scan or VectorMask."
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
