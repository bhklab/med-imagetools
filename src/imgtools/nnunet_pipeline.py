from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List

from joblib import Parallel, delayed  # type: ignore
from tqdm import tqdm

from imgtools.autopipeline import ProcessSampleResult, process_one_sample
from imgtools.coretypes.masktypes.roi_matching import (
    ROIMatchFailurePolicy,
    ROIMatchStrategy,
    Valid_Inputs as ROIMatcherInputs,
)
from imgtools.io.nnunet_output import MaskSavingStrategy, nnUNetOutput
from imgtools.io.sample_input import SampleInput
from imgtools.io.sample_output import ExistingFileMode
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


class nnUNetPipeline:  # noqa: N801
    """Pipeline for processing medical images in nnUNet format."""

    input: SampleInput
    output: nnUNetOutput
    transformer: Transformer[MedImage | VectorMask]

    def __init__(
        self,
        input_directory: str | Path,
        output_directory: str | Path,
        modalities: list[str],
        roi_match_map: ROIMatcherInputs,
        mask_saving_strategy: MaskSavingStrategy,
        existing_file_mode: ExistingFileMode = ExistingFileMode.FAIL,
        update_crawl: bool = False,
        n_jobs: int | None = None,
        roi_ignore_case: bool = True,
        roi_allow_multi_key_matches: bool = True,
        spacing: tuple[float, float, float] = (0.0, 0.0, 0.0),
        window: float | None = None,
        level: float | None = None,
    ) -> None:
        """
        Initialize the nnUNetpipeline.

        Parameters
        ----------
        input_directory : str | Path
            Directory containing the DICOM files (or subdirectories with DICOM files)
        output_directory : str | Path
            Directory to save the output nifti files
               existing_file_mode : ExistingFileMode
            How to handle existing files (FAIL, SKIP, OVERWRITE).
        modalities : list[str]
            List of modalities to include
        roi_match_map : ROIMatcherInputs
            ROI matching patterns
        mask_saving_strategy : MaskSavingStrategy
            Mask saving strateg
        update_crawl : bool, optional
            Whether to force recrawling, by default False
        n_jobs : int | None, optional
            Number of parallel jobs, by default None (uses CPU count - 2)
        roi_ignore_case : bool, optional
            Whether to ignore case in ROI matching, by default True
        roi_allow_multi_key_matches : bool, optional
            Whether to allow multiple key matches in ROI matching, by default True
        spacing : tuple[float, float, float], default=(0.0, 0.0, 0.0)
            Spacing for resampling, by default (0.0, 0.0, 0.0)
        window : float | None, optional
            Window level for intensity normalization, by default None
        level : float | None, optional
            Window level for intensity normalization, by default None
        """

        # Validate modalities
        allowed_modalities = {
            frozenset(("CT", "SEG")),
            frozenset(("MR", "SEG")),
            frozenset(("CT", "RTSTRUCT")),
            frozenset(("MR", "RTSTRUCT")),
        }
        if frozenset(modalities) not in allowed_modalities:
            msg = (
                f"Invalid modalities: {','.join(modalities)}. "
                f"Allowed combinations are: {[','.join(allowed) for allowed in allowed_modalities]}"
            )
            raise ValueError(msg)

        self.input = SampleInput.build(
            directory=Path(input_directory),
            update_crawl=update_crawl,
            n_jobs=n_jobs,
            modalities=modalities,
            roi_match_map=roi_match_map,
            roi_ignore_case=roi_ignore_case,
            roi_handling_strategy=ROIMatchStrategy.MERGE,
            roi_on_missing_regex=ROIMatchFailurePolicy.ERROR,
            roi_allow_multi_key_matches=roi_allow_multi_key_matches,
        )

        self.output = nnUNetOutput(
            directory=Path(output_directory),
            existing_file_mode=existing_file_mode,
            dataset_name=Path(input_directory).name,
            roi_keys=list(self.input.roi_matcher.match_map.keys()),
            mask_saving_strategy=mask_saving_strategy,
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
        import json

        # Load the samples
        samples = self.input.query()
        samples = sorted(samples, key=lambda x: x[0].PatientID.lower())

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
            for idx, sample in enumerate(samples, start=1)
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
                if result.success:
                    successful_results.append(result)
                    pbar.update(1)
                else:
                    failed_results.append(result)
                    pbar.update(0)

        # Log summary information
        success_count = len(successful_results)
        failure_count = len(failed_results)
        total_count = len(all_results)

        logger.info(
            f"Processing complete. {success_count} successful, {failure_count} failed "
            f"out of {total_count} total samples ({success_count / total_count * 100:.1f}% success rate)."
        )

        # Finalize output(Generate dataset.json and nnUNet scripts)
        if success_count > 0:
            self.output.finalize_dataset()

        index_file = self.output.writer.index_file
        # TODO:: discuss how we want to name these files
        # Generate report file names
        success_file = index_file.with_name(
            f"{self.output.writer.root_directory.name}_successful_{timestamp}.json"
        )
        failure_file = index_file.with_name(
            f"{self.output.writer.root_directory.name}_failed_{timestamp}.json"
        )

        # Convert results to dictionaries for JSON serialization
        success_dicts = [result.to_dict() for result in successful_results]
        failure_dicts = [result.to_dict() for result in failed_results]

        # Write reports
        # with open(success_file, "w") as f:
        with success_file.open("w", encoding="utf-8") as f:
            json.dump(success_dicts, f, indent=2)
        logger.info(f"Detailed success report saved to {success_file}")

        # if no failures, we can skip writing the failure file
        if failure_count == 0:
            return {"success": successful_results, "failure": []}

        with failure_file.open("w", encoding="utf-8") as f:
            json.dump(failure_dicts, f, indent=2)
        logger.info(f"Detailed failure report saved to {failure_file}")

        # Return all results categorized
        return {"success": successful_results, "failure": failed_results}

    def __rich_repr__(self) -> rich.repr.Result:
        """
        Rich representation of the pipeline.
        """
        yield "SampleInput", self.input
        yield "Transformer", self.transformer
        yield "nnUNetOutput", self.output


if __name__ == "__main__":
    from rich import print  # noqa

    # Interlacer parameters
    dataset_name = "RADCURE"

    # shutil.rmtree(f"temp_outputs/{dataset_name}", ignore_errors=True)
    output_path = Path("temp_outputs") / dataset_name
    output_path.mkdir(exist_ok=True, parents=True)
    pipeline = nnUNetPipeline(
        input_directory=f"data/{dataset_name}",
        output_directory=output_path,
        existing_file_mode=ExistingFileMode.OVERWRITE,
        n_jobs=10,
        modalities=["CT", "RTSTRUCT"],
        roi_match_map={
            "BRAIN": ["Brain"],
            "BRAINSTEM": ["Brainstem"],
        },
        mask_saving_strategy=MaskSavingStrategy.REGION_MASK,
    )

    print(pipeline)
    results = pipeline.run()
    # print(f"Results: {results}")
