from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence

from joblib import Parallel, delayed  # type: ignore
from tqdm import tqdm

from imgtools.autopipeline_utils import PipelineResults, save_pipeline_reports
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
from imgtools.loggers import logger, tqdm_logging_redirect
from imgtools.transforms import (
    BaseTransform,
    Resample,
    Transformer,
    WindowIntensity,
)

if TYPE_CHECKING:
    import rich.repr

    from imgtools.coretypes.base_masks import VectorMask
    from imgtools.coretypes.base_medimage import MedImage
    from imgtools.dicom.interlacer import SeriesNode


class NoValidSamplesError(Exception):
    """Exception raised when no valid samples are found."""

    def __init__(
        self,
        message: str,
        user_query: list[str] | None,
        valid_queries: list[str],
    ) -> None:
        msg = (
            f"{message}\n"
            f"User query: {user_query}\n"
            f"Valid queries: {valid_queries}\n"
            # TODO::when we write docs on the logic of modality queries,
            # we should add a link to the docs in this message
        )

        super().__init__(msg)
        self.user_query = user_query
        self.valid_queries = valid_queries


# on top of the full index csv, we create a simplified version
# that contains some of the most important columns in this order
SIMPLIFIED_COLUMNS = [
    "filepath",
    "hash",
    "saved_time",
    "SampleNumber",
    "ImageID",
    "PatientID",
    "Modality",
    "SeriesInstanceUID",
    "StudyInstanceUID",
    "ReferencedSeriesUID",
    # for Masks
    "roi_key",
    "matched_rois",
    # created from MedImage (or subclass) `fingerprint` property
    "class",
    "dtype_str",
    "dtype_numpy",
    "ndim",
    "nvoxels",
    "size",
    "spacing",
    "origin",
    "direction",
    "bbox.size",
    "bbox.min_coord",
    "bbox.max_coord",
    "sum",
    "min",
    "max",
    "mean",
    "std",
    "variance",
]


@dataclass
class ProcessSampleResult:
    """Result of processing a single sample."""

    # Sample identifier information
    sample_id: str
    sample: Sequence[SeriesNode]  # Store the entire sample

    # Output information
    output_files: List[Path] = field(default_factory=list)

    # Status information
    success: bool = False
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict] = None
    processing_time: Optional[float] = None

    @property
    def has_error(self) -> bool:
        """Check if the processing had an error."""
        return not self.success or self.error_message is not None

    def to_dict(self) -> Dict:
        """Convert the result to a dictionary."""

        base_dict = {
            "SampleID": self.sample_id,
            "PatientID": self.sample[0].PatientID if self.sample else None,
            "samples": [
                {
                    "SeriesInstanceUID": s.SeriesInstanceUID,
                    "Modality": s.Modality,
                    "folder": s.folder,
                }
                for s in self.sample
            ],
            "processing_time": f"{self.processing_time:.2f}s",
        }

        if not self.has_error:
            return {
                **base_dict,
                "output_files": [str(f) for f in self.output_files],
            }
        else:
            return {
                **base_dict,
                "error_type": self.error_type,
                "error_message": self.error_message,
                "error_details": self.error_details,
            }


def process_one_sample(
    args: tuple[
        str,
        Sequence[SeriesNode],
        SampleInput,
        Transformer,
        SampleOutput,
    ],
) -> ProcessSampleResult:
    """
    Process a single medical imaging sample through the complete pipeline.

    The single 'args' tuple contains the following elements, likely passed in
    from the components of the autopipeline class:
    - idx: str (arbitrary, generated from enumerate)
    - sample: Sequence[SeriesNode] (a sample is the group of series that belong to the same reference image)
    - sample_input: SampleInput (class that handles loading the sample)
    - transformer: Transformer (class that handles the transformation pipeline)
    - sample_output: SampleOutput (class that handles saving the sample)

    This function handles the entire lifecycle of processing a medical image sample:

    1. First, we load the sample images from the provided input source
    2. Then, we verify that all requested images were properly loaded
    3. Next, we apply the transformation pipeline to the images (resampling, windowing, etc.)
    4. Finally, we save the processed images to the output location

    Throughout this process, we track any errors that occur and return detailed
    information about successes or failures for reporting purposes.

    Returns
    -------
    ProcessSampleResult
        Result of processing the sample, including success/failure information
    """
    # TODO:: the logic for all the result information is a bit messy
    # rework it to pass in custom exception objects that get parsed in the
    # to_dict method

    start_time = time.time()

    sample: Sequence[SeriesNode]
    idx, sample, sample_input, transformer, sample_output = args

    # Initialize the result with sample information
    result = ProcessSampleResult(
        sample_id=idx,
        sample=sample,  # Store the entire sample
    )

    try:
        # Load the sample
        sample_images: Sequence[MedImage | VectorMask] = sample_input(sample)
    except Exception as e:
        error_message = str(e)
        logger.exception("Failed to load sample", e=e)
        result.error_type = "LoadError"
        result.error_message = f"Failed to load sample: {error_message}"
        result.processing_time = time.time() - start_time
        return result

    # by this point all images SHOULD have some bare minimum
    # metadata attribute, which should have the SeriesInstanceUID
    # lets just quickly validate that the unique list of SeriesInstanceUIDs
    # in our input 'samples' is the same as the unique list of SeriesInstanceUIDs
    # in our loaded sample_images
    series_instance_uids = {s.SeriesInstanceUID for s in sample}
    loaded_series_instance_uids = {
        s.metadata.get("SeriesInstanceUID", None) for s in sample_images
    }

    # check if our input samples is a subset of our loaded sample_images
    # we use subset, because we may have loaded more images than requested (subseries)
    if not series_instance_uids.issubset(loaded_series_instance_uids):
        error_msg = (
            f"Loaded {len(loaded_series_instance_uids)} sample"
            f" images do not match input samples {len(series_instance_uids)}. "
            "This most likely may be due to failures to match ROIs. "
            f"We will save {len(loaded_series_instance_uids)} loaded, "
            f"out of {len(series_instance_uids)} input series. "
        )
        result.error_type = "ROIMatchError"
        result.error_message = error_msg
        result.error_details = {
            "loaded_series": list(loaded_series_instance_uids),
            "input_series": list(series_instance_uids),
        }

    try:
        transformed_images = transformer(sample_images)
    except Exception as e:
        error_message = str(e)
        result.error_type = "TransformError"
        result.error_message = f"Failed during transformation: {error_message}"
        result.processing_time = time.time() - start_time
        return result

    try:
        saved_files = sample_output(
            transformed_images,
            SampleNumber=idx,
        )
        result.output_files = list(saved_files)
        if not result.output_files:
            raise ValueError(
                "No output files were saved. Check the output directory."
            )
        result.success = True
    except Exception as e:
        error_message = str(e)
        result.error_type = "SaveError"
        result.error_message = f"Failed to save output: {error_message}"
        result.processing_time = time.time() - start_time
        return result

    result.processing_time = time.time() - start_time
    return result


class Autopipeline:
    """Pipeline for processing medical images."""

    input: SampleInput
    output: SampleOutput
    transformer: Transformer[MedImage | VectorMask]

    def __init__(
        self,
        input_directory: str | Path,
        output_directory: str | Path,
        output_filename_format: str = DEFAULT_FILENAME_FORMAT,
        existing_file_mode: ExistingFileMode = ExistingFileMode.FAIL,
        update_crawl: bool = False,
        n_jobs: int | None = None,
        modalities: list[str] | None = None,
        roi_match_map: ROIMatcherInputs = None,
        roi_ignore_case: bool = True,
        roi_handling_strategy: str
        | ROIMatchStrategy = ROIMatchStrategy.SEPARATE,
        roi_allow_multi_key_matches: bool = True,
        roi_on_missing_regex: str | ROIMatchFailurePolicy = (
            ROIMatchFailurePolicy.WARN
        ),
        spacing: tuple[float, float, float] = (0.0, 0.0, 0.0),
        window: float | None = None,
        level: float | None = None,
    ) -> None:
        """
        Initialize the Autopipeline.

        Parameters
        ----------
        input_directory : str | Path
            Directory containing the DICOM files (or subdirectories with DICOM files)
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
            By default ROIMatchFailurePolicy.WARN
        spacing : tuple[float, float, float], default=(0.0, 0.0, 0.0)
            Spacing for resampling, by default (0.0, 0.0, 0.0)
        window : float | None, optional
            Window level for intensity normalization, by default None
        level : float | None, optional
            Window level for intensity normalization, by default None
        """
        self.input = SampleInput.build(
            directory=Path(input_directory),
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
            extra_context={},
        )

        transforms: list[BaseTransform] = [
            # we could choose to only add resampling if any spacing component
            # is non-zero, but this currently does additional non-intuitive
            # alignment by assuming the first image in the sample is the reference
            # and all other images get resampled to that via sitk.Resample
            Resample(
                spacing,
                interpolation="linear",
                anti_alias=True,
                anti_alias_sigma=None,
                transform=None,
                output_size=None,
            ),
        ]

        if window is not None and level is not None:
            transforms.append(WindowIntensity(window=window, level=level))

        self.transformer = Transformer(transforms)

        logger.info("Pipeline initialized")

    def run(
        self,
    ) -> Dict[str, List[ProcessSampleResult]]:
        """
        Run the pipeline on all samples.

        Returns
        -------
        Dict[str, List[ProcessSampleResult]]
            Dictionary with 'success' and 'failure' keys, each containing a list of
            ProcessSampleResult objects.
        """

        # Load the samples
        samples = self.input.query()
        samples = sorted(samples, key=lambda x: x[0].PatientID.lower())

        if not samples:
            raise NoValidSamplesError(
                message="No valid samples found.",
                user_query=self.input.modalities,
                valid_queries=self.input.interlacer.valid_queries,
            )

        # Create a timestamp for this run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Prepare arguments for parallel processing
        arg_tuples = [
            (
                f"{idx:04}",
                sample,
                self.input,
                self.transformer,
                self.output,
            )
            for idx, sample in enumerate(samples)
        ]

        # Lists to track results
        all_results = []
        successful_results = []
        failed_results = []

        with (
            tqdm_logging_redirect(),
            tqdm(
                total=len(arg_tuples),
                desc="Processing samples",
                unit="sample",
            ) as pbar,
        ):
            # Process samples in parallel
            for result in Parallel(
                n_jobs=self.input.n_jobs,
                backend="loky",
                return_as="generator",
            )(delayed(process_one_sample)(arg) for arg in arg_tuples):
                all_results.append(result)

                # Update progress bar and track results by success/failure
                if not result.has_error:
                    successful_results.append(result)
                else:
                    failed_results.append(result)
                pbar.update(1)

        # Create pipeline results object
        pipeline_results = PipelineResults(
            successful_results=successful_results,
            failed_results=failed_results,
            all_results=all_results,
            timestamp=timestamp,
        )

        # Save reports and get file paths
        save_pipeline_reports(
            results=pipeline_results,
            index_file=self.output.writer.index_file,
            root_dir_name=self.output.writer.root_directory.name,
            simplified_columns=SIMPLIFIED_COLUMNS,
            index_lock_check_func=self.output.writer._get_index_lock,
        )

        # Return all results categorized
        return pipeline_results.to_dict()

    def __rich_repr__(self) -> rich.repr.Result:
        """
        Rich representation of the pipeline.
        """
        yield "SampleInput", self.input
        yield "Transformer", self.transformer
        yield "SampleOutput", self.output


if __name__ == "__main__":
    import shutil

    from rich import print  # noqa

    # Interlacer parameters
    dataset_name = "RADCURE"

    shutil.rmtree(f"temp_outputs/{dataset_name}", ignore_errors=True)
    pipeline = Autopipeline(
        input_directory=f"data/{dataset_name}",
        output_directory=f"temp_outputs/{dataset_name}",
        existing_file_mode=ExistingFileMode.OVERWRITE,
        n_jobs=10,
        modalities=["all"],
        roi_match_map={
            "GTV": ["GTVp"],
            "NODES": ["GTVn_.*"],
            "LPLEXUS": ["BrachialPlex_L"],
            "RPLEXUS": ["BrachialPlex_R"],
            "BRAINSTEM": ["Brainstem"],
            "LACOUSTIC": ["Cochlea_L"],
            "RACOUSTIC": ["Cochlea_R"],
            "ESOPHAGUS": ["Esophagus"],
            "LEYE": ["Eye_L"],
            "REYE": ["Eye_R"],
            "LARYNX": ["Larynx"],
            "LLENS": ["Lens_L"],
            "RLENS": ["Lens_R"],
            "LIPS": ["Lips"],
            "MANDIBLE": ["Mandible_Bone"],
            "LOPTIC": ["Nrv_Optic_L"],
            "ROPTIC": ["Nrv_Optic_R"],
            "CHIASM": ["OpticChiasm"],
            "LPAROTID": ["Parotid_L"],
            "RPAROTID": ["Parotid_R"],
            "CORD": ["SpinalCord"],
        },
        roi_allow_multi_key_matches=False,
        roi_ignore_case=True,
        roi_handling_strategy=ROIMatchStrategy.SEPARATE,
        roi_on_missing_regex=ROIMatchFailurePolicy.IGNORE,
    )

    print(pipeline)
    # results = pipeline.run(first_n=1)
    # print(f"Results: {results}")
