from __future__ import annotations

import multiprocessing
import os
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Sequence, cast

from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    field_validator,
    model_validator,
)

from imgtools.coretypes import MedImage
from imgtools.coretypes.masktypes.roi_matching import (
    ROIMatcher,
    ROIMatchFailurePolicy,
    ROIMatchStrategy,
    Valid_Inputs as ROIMatcherInputs,
    create_roi_matcher,
)
from imgtools.coretypes.masktypes.seg import SEG
from imgtools.coretypes.masktypes.structureset import RTStructureSet
from imgtools.dicom.crawl import Crawler
from imgtools.dicom.interlacer import Interlacer, SeriesNode
from imgtools.io.readers import MedImageT, read_dicom_auto
from imgtools.loggers import logger

if TYPE_CHECKING:
    from imgtools.coretypes.base_masks import VectorMask

__all__ = ["SampleInput"]


class SampleInput(BaseModel):
    """
    Configuration model for processing medical imaging samples.

    This class provides a standardized configuration for loading and processing
    medical imaging data, including DICOM crawling and ROI matching settings.

    Attributes
    ----------
    directory : Path
        Directory containing the input files. Must exist and be readable.
    dataset_name : str | None
        Optional name for the dataset. Defaults to the base name of the input directory.
    update_crawl : bool
        Whether to force a new crawl even if one exists. Default is False.
    n_jobs : int
        Number of jobs to run in parallel. Default is (CPU cores - 2) or 1.
    modalities : list[str] | None
        List of modalities to include. None means include all modalities.
    roi_matcher : ROIMatcher
        Configuration for matching regions of interest in the images.


    Examples
    --------
    >>> from imgtools.io.loaders.sample_input import (
    ...     SampleInput,
    ... )
    >>> config = SampleInput(
    ...     directory="data/NSCLC-Radiomics"
    ... )
    >>> config.dataset_name
    'NSCLC-Radiomics'

    >>> # Using the factory method with ROI matching parameters
    >>> config = SampleInput.build(
    ...     directory="data/NSCLC-Radiomics",
    ...     roi_match_map={
    ...         "GTV": ["GTV.*"],
    ...         "PTV": ["PTV.*"],
    ...     },
    ...     roi_ignore_case=True,
    ...     roi_handling_strategy="merge",
    ... )
    """

    directory: Path = Field(
        description="Path to the input directory containing DICOM files. Absolute path or relative to the current working directory.",
        title="Input Directory",
        examples=["data/NSCLC-Radiomics", "/absolute/path/to/dicom/data"],
        json_schema_extra={
            "format": "path",
            "pattern": "^[^\\0]+$",  # Non-null characters
            "x-descriptive": "Directory with standard DICOM files for processing",
        },
    )
    dataset_name: str | None = Field(
        default=None,
        description="Name of the dataset, defaults to input directory base name if not provided. Used for organizing outputs and labeling results.",
        title="Dataset Name",
        min_length=1,
        max_length=100,
        examples=["NSCLC-Radiomics", "Head-Neck-PET-CT"],
        json_schema_extra={"x-display-name": "Dataset Identifier"},
    )
    update_crawl: bool = Field(
        default=False,
        description="Force recrawl even if crawl data already exists. Set to True when directory contents have changed or to refresh metadata cache.",
        title="Update DICOM Crawl",
        json_schema_extra={"x-display-name": "Force Directory Recrawl"},
    )
    n_jobs: int = Field(
        default=max(1, multiprocessing.cpu_count() - 2),
        description="Number of parallel jobs to run for DICOM processing. Default reserves 2 cores for system operations.",
        title="Parallel Jobs",
        ge=1,  # Greater than or equal to 1
        le=multiprocessing.cpu_count(),  # Less than or equal to available cores
        examples=[4, 8, 12],
        json_schema_extra={
            "x-category": "Performance",
            "x-recommended-range": f"1-{multiprocessing.cpu_count()}",
        },
    )
    modalities: list[str] | None = Field(
        default=None,
        description="List of DICOM modalities to include in processing. None means include all modalities. Common values include 'CT', 'MR', 'PT', 'RTSTRUCT', 'RTDOSE', 'SEG'.",
        title="DICOM Modalities",
        examples=[
            ["CT", "RTSTRUCT"],
            ["CT", "PT", "RTSTRUCT", "RTDOSE"],
            ["MR", "SEG"],
        ],
        json_schema_extra={
            "items": {
                "enum": [
                    "CT",
                    "MR",
                    "PT",
                    "RTSTRUCT",
                    "RTDOSE",
                    "RTPLAN",
                    "SEG",
                ]
            },
            "x-modality-dependencies": {
                "RTSTRUCT": ["CT", "MR", "PT"],
                "RTDOSE": ["CT", "MR", "PT"],
                "SEG": ["CT", "MR"],
            },
        },
    )
    roi_matcher: ROIMatcher = Field(
        default_factory=lambda: ROIMatcher(match_map={"ROI": [".*"]}),
        description="Configuration for ROI (Region of Interest) matching in segmentation data. Defines how regions are identified, matched and processed from RTSTRUCT or SEG files.",
        title="ROI Matcher Configuration",
        json_schema_extra={
            "x-examples": [
                {
                    "match_map": {"GTV": ["GTV.*"], "PTV": ["PTV.*"]},
                    "handling_strategy": "merge",
                    "ignore_case": True,
                },
                {
                    "match_map": {
                        "Tumor": [".*tumor.*", ".*gtv.*"],
                        "OAR": [".*organ.*", ".*risk.*"],
                    },
                    "handling_strategy": "separate",
                },
            ],
            "x-documentation": "See ROIMatcher class documentation for detailed usage examples",
        },
    )
    _crawler: Crawler | None = PrivateAttr(default=None, init=False)
    _interlacer: Interlacer | None = PrivateAttr(default=None, init=False)

    def model_post_init(self, __context) -> None:  # type: ignore # noqa: ANN001
        """Initialize the Crawler instance after model initialization."""
        crawler = Crawler(
            dicom_dir=self.directory,
            dataset_name=self.dataset_name,
            force=self.update_crawl,
            n_jobs=self.n_jobs,
        )
        crawler.crawl()
        self._crawler = crawler
        self._interlacer = Interlacer(crawl_index=crawler.index)

    @field_validator("directory")
    @classmethod
    def validate_directory(cls, v: str | Path) -> Path:
        """Validate that the input directory exists and is readable."""
        path = Path(v) if not isinstance(v, Path) else v

        if not path.exists():
            msg = f"Input directory does not exist: {path}"
            raise ValueError(msg)

        if not path.is_dir():
            msg = f"Input path must be a directory: {path}"
            raise ValueError(msg)

        if not os.access(path, os.R_OK):
            msg = f"Input directory is not readable: {path}"
            raise ValueError(msg)

        return path

    @field_validator("n_jobs")
    @classmethod
    def validate_n_jobs(cls, v: int) -> int:
        """Validate that n_jobs is reasonable."""
        cpu_count = multiprocessing.cpu_count()

        if v <= 0:
            logger.warning("n_jobs must be positive, using default")
            return max(1, cpu_count - 2)

        if v > cpu_count:
            logger.warning(
                f"n_jobs ({v}) exceeds available CPU count ({cpu_count}), "
                f"setting to {cpu_count}"
            )
            return cpu_count

        return v

    @field_validator("modalities")
    @classmethod
    def validate_modalities(cls, v: list[str] | None) -> list[str] | None:
        """Validate that modalities are a list of strings."""
        if v is None:
            return v

        if not all(isinstance(m, str) for m in v):
            raise ValueError("Modalities must be a list of strings")

        return v

    @model_validator(mode="after")
    def set_default_dataset_name(self) -> "SampleInput":
        """Set default dataset name if not provided."""
        if self.dataset_name is None:
            self.dataset_name = self.directory.name
            logger.debug(
                f"Using input directory name as dataset name: {self.dataset_name}"
            )

        return self

    @classmethod
    def build(
        cls,
        directory: str | Path,
        dataset_name: str | None = None,
        update_crawl: bool = False,
        n_jobs: int | None = None,
        modalities: list[str] | None = None,
        roi_match_map: ROIMatcherInputs = None,
        roi_ignore_case: bool = True,
        roi_handling_strategy: str | ROIMatchStrategy = ROIMatchStrategy.MERGE,
        roi_allow_multi_key_matches: bool = True,
        roi_on_missing_regex: str | ROIMatchFailurePolicy = (
            ROIMatchFailurePolicy.IGNORE
        ),
    ) -> "SampleInput":
        """Create a SampleInput with separate parameters for ROIMatcher.

        This factory method allows users to specify ROIMatcher parameters directly
        instead of constructing a objects separately.

        Parameters
        ----------
        directory : str | Path
            Directory containing the input files
        dataset_name : str | None, optional
            Name of the dataset, by default None (uses input directory name)
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

        Returns
        -------
        SampleInput
            Configured SampleInput instance
        """
        # Convert string strategy to enum if needed
        if isinstance(roi_handling_strategy, str):
            roi_handling_strategy = ROIMatchStrategy(
                roi_handling_strategy.lower()
            )

        if isinstance(roi_on_missing_regex, str):
            roi_on_missing_regex = ROIMatchFailurePolicy(
                roi_on_missing_regex.lower()
            )

        # Create the ROIMatcher
        roi_matcher = create_roi_matcher(
            roi_match_map,
            handling_strategy=roi_handling_strategy,
            ignore_case=roi_ignore_case,
            allow_multi_key_matches=roi_allow_multi_key_matches,
            on_missing_regex=roi_on_missing_regex,
        )
        num_jobs = n_jobs or max(1, multiprocessing.cpu_count() - 2)

        # Create the SampleInput
        return cls(
            directory=Path(directory),
            dataset_name=dataset_name,
            update_crawl=update_crawl,
            n_jobs=num_jobs,
            modalities=modalities,
            roi_matcher=roi_matcher,
        )

    @classmethod
    def default(cls) -> "SampleInput":
        """Create a default SampleInput instance."""
        return cls.build(directory="./data")

    ###################################################################
    # Interlacer methods
    ###################################################################

    @property
    def crawler(self) -> Crawler:
        """Get the Crawler instance."""
        if self._crawler is None:
            raise ValueError("Crawler has not been initialized.")
        return self._crawler

    @property
    def interlacer(self) -> Interlacer:
        """Get the Interlacer instance."""
        if self._interlacer is None:
            raise ValueError("Interlacer has not been initialized.")
        return self._interlacer

    def print_tree(self) -> None:
        self.interlacer.print_tree(input_directory=self.directory)

    def query(self, modalities: str) -> list[list[SeriesNode]]:
        """Query the interlacer for a specific modality."""
        return self.interlacer.query(modalities)

    ###################################################################
    # Loading methods
    ###################################################################

    def _read_series(
        self,
        series_uid: str,
        modality: str,
        folder: str,
        load_subseries: bool = False,
    ) -> list[MedImageT]:
        # we assume that all subseries are in the same directory
        root_dir = self.directory.parent / folder

        if not root_dir.exists():
            msg = f"Directory does not exist: {root_dir}"
            raise FileNotFoundError(msg)

        file_name_sets = []
        series_info = self.crawler.crawl_db_raw[series_uid]
        if load_subseries:
            for subseries in series_info:
                file_name_sets.append(
                    [
                        (root_dir / file_name).as_posix()
                        for file_name in series_info[subseries][
                            "instances"
                        ].values()
                    ]
                )
        else:
            if len(series_info) > 1:
                msg = (
                    f"Series {series_uid} contains multiple subseries, but "
                    "load_subseries is set to False. Combining into one image."
                )
                logger.warning(msg, folder=folder, modality=modality)
            file_name_sets.append(
                [
                    (root_dir / file_name).as_posix()
                    for subseries in series_info
                    for file_name in series_info[subseries][
                        "instances"
                    ].values()
                ]
            )

        # load the series
        return [
            read_dicom_auto(
                path=root_dir.as_posix(),
                modality=modality,
                file_names=file_name_set,
                series_id=series_uid,
            )
            for file_name_set in file_name_sets
        ]

    def load_sample(  # noqa: PLR0912
        self,
        sample: Sequence[SeriesNode],
        load_subseries: bool = False,
    ) -> Sequence[MedImage | VectorMask]:
        # group list by modality
        by_mod: defaultdict[str, list[SeriesNode]] = defaultdict(list)
        for series in sample:
            by_mod[series.Modality].append(series)

        reference_modality = (
            "CT"
            if "CT" in by_mod
            else "MR"
            if "MR" in by_mod
            else "PT"
            if "PT" in by_mod
            else None
        )
        if not reference_modality:
            raise ValueError(
                "No CT, MR, or PT series found to use as reference."
            )
        if len(by_mod[reference_modality]) > 1:
            msg = (
                f"Found {len(by_mod[reference_modality])} "
                f"{reference_modality} series, "
                "using the first one as reference."
            )
            logger.warning(msg, reference_list=by_mod[reference_modality])

        # Load the first found reference series
        reference_series = by_mod[reference_modality].pop(0)
        reference_images = self._read_series(
            series_uid=reference_series.SeriesInstanceUID,
            modality=reference_modality,
            folder=reference_series.folder,
            load_subseries=load_subseries,
        )

        images: Sequence[MedImage] = []

        # hack to satisfy mypy for now
        reference_scans = cast("list[MedImage]", reference_images)

        # Extract the first (of possibly many subseries) as the reference image
        reference_image = reference_scans[0]
        images = reference_scans[1:]
        # Load the rest of the series
        for modality, series_nodes in by_mod.items():
            if modality == reference_modality:
                # TODO:: maybe implement some check here in case we loading
                # another of same reference modality?
                continue

            # for all other series, we load them and insert them into the
            # images list
            self._load_non_ref_images(
                load_subseries,
                images,
                reference_image,
                modality,
                series_nodes,
            )

        return [reference_image] + images

    def _load_non_ref_images(
        self,
        load_subseries: bool,
        images: list[MedImage | VectorMask],
        reference_image: MedImage,
        modality: str,
        series_nodes: list[SeriesNode],
    ) -> None:
        for series in series_nodes:
            match modality:
                case "RTSTRUCT" | "SEG":
                    mask_klass = (
                        RTStructureSet if modality == "RTSTRUCT" else SEG
                    )
                    vm = mask_klass.from_dicom(
                        dicom=self.directory.parent / series.folder
                    ).get_vector_mask(
                        reference_image=reference_image,
                        roi_matcher=self.roi_matcher,
                    )
                    if vm is None:
                        continue
                    images.append(vm)
                case "PT" | "CT" | "MR" | "RTDOSE":
                    misc = self._read_series(
                        series_uid=series.SeriesInstanceUID,
                        modality=modality,
                        folder=series.folder,
                        load_subseries=load_subseries,
                    )
                    # if len (misc) > 1, that means that somehow a non-reference
                    # image has multiple subseries, which is not expected
                    # and we should handle this at some point
                    assert isinstance(misc[0], MedImage) and len(misc) == 1
                    images.append(misc[0])
                case _:
                    msg = f"Unsupported modality: {modality}"
                    raise ValueError(msg)


if __name__ == "__main__":  # pragma: no cover
    from rich import print  # noqa: A004, F401
    from tqdm import tqdm  # noqa: A003

    from imgtools.io.sample_output import ExistingFileMode, SampleOutput
    from imgtools.loggers import tqdm_logging_redirect

    medinput = SampleInput(
        directory=Path("data/RADCURE"),
        update_crawl=True,
        n_jobs=12,
        dataset_name="RADCURE",
        modalities=["CT", "RTSTRUCT"],
        roi_matcher=ROIMatcher(
            match_map={
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
            allow_multi_key_matches=False,  # if True, an ROI can match multiple keys
            handling_strategy=ROIMatchStrategy.SEPARATE,
            ignore_case=True,
            on_missing_regex=ROIMatchFailurePolicy.WARN,
        ),
    )
    medoutput = SampleOutput(
        directory=Path("temp_outputs/RADCURE_PROCESSED"),
        existing_file_mode=ExistingFileMode.OVERWRITE,
    )
    query_string = "CT,RTSTRUCT"

    sample_sets = medinput.interlacer.query(
        query_string=query_string,
        group_by_root=True,
    )
    with tqdm_logging_redirect():
        for series in tqdm(
            sample_sets,
            desc="Loading series",
            unit="series",
            leave=False,
            total=len(sample_sets),
        ):
            try:
                result = medinput.load_sample(
                    sample=series,
                    load_subseries=False,
                )
            except ValueError as e:
                logger.error(f"Error loading series: {e}")
                continue
            medoutput(result)
