from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Sequence

from imgtools.coretypes.masktypes.roi_matching import (
    ROIMatchFailurePolicy,
    ROIMatchStrategy,
    Valid_Inputs as ROIMatcherInputs,
)
from imgtools.io.sample_input import SampleInput
from imgtools.io.sample_output import (
    DEFAULT_FILENAME_FORMAT,
    ExistingFileMode,
    SampleOutput,
)
from imgtools.transforms import (
    BaseTransform,
    Resample,
    Transformer,
    WindowIntensity,
)

if TYPE_CHECKING:
    from imgtools.coretypes.base_masks import VectorMask
    from imgtools.coretypes.base_medimage import MedImage
    from imgtools.dicom.interlacer import SeriesNode


class DeltaPipeline:
    """Pipeline for processing medical images."""

    input: SampleInput
    output: SampleOutput
    transformer: Transformer[MedImage | VectorMask]

    # Interlacer parameters
    query: str = "CT,RTSTRUCT"

    # Transformer parameters
    spacing: tuple[float, float, float] = (1.0, 1.0, 0.0)
    window: float | None = None
    level: float | None = None

    def __init__(
        self,
        input_directory: str | Path,
        output_directory: str | Path,
        output_filename_format: str = DEFAULT_FILENAME_FORMAT,
        existing_file_mode: ExistingFileMode = ExistingFileMode.FAIL,
        dataset_name: str | None = None,
        update_crawl: bool = False,
        n_jobs: int | None = None,
        modalities: list[str] | None = None,
        roi_match_map: ROIMatcherInputs = None,
        roi_ignore_case: bool = True,
        roi_handling_strategy: str | ROIMatchStrategy = ROIMatchStrategy.MERGE,
        roi_allow_multi_key_matches: bool = True,
        roi_on_missing_regex: str | ROIMatchFailurePolicy = (
            ROIMatchFailurePolicy.WARN
        ),
    ) -> None:
        """
        Initialize the DeltaPipeline.

        Parameters
        ----------
        input_directory : str | Path
            Directory containing the input files
        dataset_name : str | None, optional
            Name of the dataset, by default None (uses input directory name)
        output_directory : str | Path
            Directory to save the output nifti files
        output_filename_format : str
            Format string for output filenames with placeholders for metadata values.
        existing_file_mode : ExistingFileMode
            How to handle existing files (FAIL, SKIP, OVERWRITE).
        update_crawl : bool, optional
            Whether to force recrawling, by default False
        n_jobs : int | None, optional
            Number of parallel jobs, by default None (uses CPU count - 2)
        modalities : list[str] | None, optional
            List of modalities to include, by default None (all)
        roi_match_map : ROIMatcherInputs, optional
            ROI matching patterns, by default None
        roi_ignore_case : bool, optional
            Whether to ignore case in ROI matching, by default True
        roi_handling_strategy : str | ROIMatchStrategy, optional
            Strategy for handling ROI matches, by default ROIMatchStrategy.MERGE
        roi_allow_multi_key_matches : bool, default=True
            Whether to allow one ROI to match multiple keys in the match_map.
        roi_on_missing_regex : str | ROIMatchFailurePolicy, optional
            How to handle when no ROI matches any pattern in match_map.
        """
        self.input = SampleInput.build(
            directory=Path(input_directory),
            dataset_name=dataset_name,
            update_crawl=update_crawl,
            n_jobs=n_jobs,
            modalities=modalities,
            roi_match_map=roi_match_map,
            roi_ignore_case=roi_ignore_case,
            roi_handling_strategy=roi_handling_strategy,
            roi_allow_multi_key_matches=roi_allow_multi_key_matches,
            roi_on_missing_regex=roi_on_missing_regex,
        )
        self.output = SampleOutput(
            directory=Path(output_directory),
            filename_format=output_filename_format,
            existing_file_mode=existing_file_mode,
        )

        transforms: list[BaseTransform]
        transforms = [
            Resample(
                self.spacing,
                interpolation="linear",
                anti_alias=True,
                anti_alias_sigma=None,
                transform=None,
                output_size=None,
            ),
        ]

        if self.window is not None and self.level is not None:
            transforms.append(
                WindowIntensity(window=self.window, level=self.level)
            )

        self.transformer = Transformer(transforms)

    def process_one_sample(self, sample: Sequence[SeriesNode]) -> None:
        """
        Process a single sample.
        """
        # Load the sample
        sample_images: Sequence[MedImage | VectorMask] = (
            self.input.load_sample(sample)
        )

        transformed_images = self.transformer(sample_images)

        self.output(transformed_images)


if __name__ == "__main__":
    from rich import print  # noqa: A004

    dataset_name = "HNSCC"

    pipeline = DeltaPipeline(
        input_directory=f"data/{dataset_name}",
        output_directory=f"temp_outputs/{dataset_name}",
        existing_file_mode=ExistingFileMode.OVERWRITE,
        n_jobs=10,
        modalities=["CT", "RTSTRUCT"],
        roi_match_map={
            # "GTV": [".*"],
            "PTV": [".*PTV.*"],
        },
        roi_handling_strategy=ROIMatchStrategy.SEPARATE,
    )

    print(pipeline)
    pipeline.process_one_sample(pipeline.input.query("CT,RTSTRUCT")[0])
