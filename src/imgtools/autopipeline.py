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
from imgtools.loggers import logger, tqdm_logging_redirect
from imgtools.transforms import (
    BaseTransform,
    Resample,
    Transformer,
    WindowIntensity,
)
from joblib import Parallel, delayed
if TYPE_CHECKING:
    import rich.repr

    from imgtools.coretypes.base_masks import VectorMask
    from imgtools.coretypes.base_medimage import MedImage
    from imgtools.dicom.interlacer import SeriesNode

from tqdm.contrib.concurrent import process_map
from tqdm.std import tqdm as std_tqdm

def process_one_sample(
    args: tuple[str, Sequence[SeriesNode], SampleInput, Transformer, SampleOutput]
) -> Sequence[Path]:
    """
    Process a single sample.
    """
    sample: Sequence[SeriesNode]
    idx, sample, sample_input, transformer, sample_output = args
    try:
        # Load the sample
        sample_images: Sequence[MedImage | VectorMask] = (
            sample_input.load_sample(sample)
        )
    except Exception as e:
        logger.exception("Failed to load sample", e=e)
        return []

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
    if not series_instance_uids.issubset(loaded_series_instance_uids):
        logger.warning(
            f"Loaded {len(loaded_series_instance_uids)} sample"
            f" images do not match input samples {len(series_instance_uids)}. "
            "This most likely may be due to failures to match ROIs. "
            f"The {len(sample_images)} will not be processed or saved. ",
            loaded_series=loaded_series_instance_uids,
            input_samples=sample,
        )
        return []
    transformed_images = transformer(sample_images)

    saved_files = sample_output(
        transformed_images,
        SampleNumber=idx,
    )

    return saved_files

class DeltaPipeline:
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
        Initialize the DeltaPipeline.

        Parameters
        ----------
        input_directory : str | Path
            Directory containing the input files
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

    def run(self, first_n: int | None = None) -> Sequence[Path]:
        """
        Run the pipeline.
        """
        # Load the samples
        samples = self.input.query()
        samples = sorted(samples, key=lambda x: x[0].PatientID.lower())

        arg_tuples = [
            (
                f"{idx:04}", 
                sample,
                self.input,
                self.transformer,
                self.output,
            ) for idx, sample in enumerate(samples)
        ]

        with tqdm_logging_redirect():
            result = Parallel(n_jobs=self.input.n_jobs, backend="loky")(
            delayed(process_one_sample)(arg)
            for arg in (arg_tuples[:first_n] if first_n is not None else arg_tuples)
            )
            logger.info(f"Processed {len(result)} samples.")

        return result

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
    query: str = "CT,RTSTRUCT"
    dataset_name = "RADCURE"

    shutil.rmtree(f"temp_outputs/{dataset_name}", ignore_errors=True)
    pipeline = DeltaPipeline(
        input_directory=f"data/{dataset_name}",
        output_directory=f"temp_outputs/{dataset_name}",
        existing_file_mode=ExistingFileMode.OVERWRITE,
        n_jobs=10,
        modalities=["CT", "RTSTRUCT"],
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

    # print(pipeline)
    # results = pipeline.run(first_n=1)
    # print(f"Results: {results}")
