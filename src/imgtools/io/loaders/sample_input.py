from __future__ import annotations

import multiprocessing
import os
from collections import defaultdict
from pathlib import Path
from typing import cast

from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    field_validator,
    model_validator,
)

from imgtools.coretypes import MedImage
from imgtools.coretypes.base_masks import VectorMask
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

__all__ = ["SampleInput"]


class SampleInput(BaseModel):
    """
    Configuration model for processing medical imaging samples.

    This class provides a standardized configuration for loading and processing
    medical imaging data, including DICOM crawling and ROI matching settings.

    Attributes
    ----------
    input_directory : Path
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
    ...     input_directory="data/NSCLC-Radiomics"
    ... )
    >>> config.dataset_name
    'NSCLC-Radiomics'

    >>> # Using the factory method with ROI matching parameters
    >>> config = SampleInput.build(
    ...     input_directory="data/NSCLC-Radiomics",
    ...     roi_match_map={
    ...         "GTV": ["GTV.*"],
    ...         "PTV": ["PTV.*"],
    ...     },
    ...     roi_ignore_case=True,
    ...     roi_handling_strategy="merge",
    ... )
    """

    input_directory: Path = Field(
        description="Directory containing the input files"
    )
    dataset_name: str | None = Field(
        None,
        description="Name of the dataset, defaults to input directory base name",
    )
    update_crawl: bool = Field(
        False, description="Force recrawl even if crawl data already exists"
    )
    n_jobs: int = Field(
        max(1, multiprocessing.cpu_count() - 2),
        description="Number of parallel jobs to run",
    )
    modalities: list[str] | None = Field(
        None, description="List of modalities to include (None = all)"
    )
    roi_matcher: ROIMatcher = Field(
        default_factory=lambda: ROIMatcher(match_map={"ROI": [".*"]}),
        description="Configuration for ROI matching",
    )
    _crawler: Crawler | None = PrivateAttr(default=None, init=False)
    _interlacer: Interlacer | None = PrivateAttr(default=None, init=False)

    def model_post_init(self, __context) -> None:  # type: ignore # noqa: ANN001
        """Initialize the Crawler instance after model initialization."""
        crawler = Crawler(
            dicom_dir=self.input_directory,
            dataset_name=self.dataset_name,
            force=self.update_crawl,
            n_jobs=self.n_jobs,
        )
        crawler.crawl()
        self._crawler = crawler
        self._interlacer = Interlacer(crawl_index=crawler.index)

    @field_validator("input_directory")
    @classmethod
    def validate_input_directory(cls, v: str | Path) -> Path:
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
            self.dataset_name = self.input_directory.name
            logger.debug(
                f"Using input directory name as dataset name: {self.dataset_name}"
            )

        return self

    @classmethod
    def build(
        cls,
        input_directory: str | Path,
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
        input_directory : str | Path
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
            input_directory=Path(input_directory),
            dataset_name=dataset_name,
            update_crawl=update_crawl,
            n_jobs=num_jobs,
            modalities=modalities,
            roi_matcher=roi_matcher,
        )

    @classmethod
    def default(cls) -> "SampleInput":
        """Create a default SampleInput instance."""
        return cls.build(input_directory=Path.cwd())

    @property
    def crawler(self) -> Crawler:
        """Get the Crawler instance."""
        if self._crawler is None:
            raise ValueError("Crawler has not been initialized.")
        return self._crawler

    ###################################################################
    # Interlacer methods
    ###################################################################

    @property
    def interlacer(self) -> Interlacer:
        """Get the Interlacer instance."""
        if self._interlacer is None:
            raise ValueError("Interlacer has not been initialized.")
        return self._interlacer

    def print_tree(self) -> None:
        self.interlacer.print_tree(input_directory=self.input_directory)

    def query(self, modalities: str) -> list[list[dict[str, str]]] | None:
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
        root_dir = self.input_directory.parent / folder

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

    def _load_series(  # noqa: PLR0912
        self,
        sample: list[SeriesNode],
        load_subseries: bool = False,
    ) -> list[MedImage | VectorMask]:
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
                f"Found {len(by_mod[reference_modality])}"
                f"{reference_modality} series,"
                " using the first one as reference."
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
        if len(reference_images) > 1:
            msg = (
                f"Found multiple {reference_modality} sub"
                "series, using the first one as reference."
            )
            logger.warning(msg, numsubseries=len(reference_images))

        images: list[MedImage | VectorMask] = []

        images.extend(
            cast("list[MedImage]", reference_images)
        )  # hack to satisfy mypy
        reference_image = images[0]
        images = images[1:]
        # Load the rest of the series
        for modality, series_nodes in by_mod.items():
            if modality == reference_modality:
                # TODO:: maybe implement some check here in case we loading
                # another of same reference modality?
                continue
            for series in series_nodes:
                match modality:
                    case "RTSTRUCT":
                        rt = RTStructureSet.from_dicom(
                            dicom=self.input_directory.parent / series.folder
                        )
                        vm = VectorMask.from_rtstruct(
                            reference_image=reference_image,
                            rtstruct=rt,
                            roi_matcher=self.roi_matcher,
                        )
                        if vm is None:
                            continue
                        images.append(vm)
                    case "SEG":
                        seg = SEG.from_dicom(
                            dicom=self.input_directory.parent / series.folder
                        )
                        vm = VectorMask.from_seg(
                            reference_image=reference_image,
                            seg=seg,
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
                        assert isinstance(misc[0], MedImage) and len(misc) == 1
                        images.append(misc[0])
                    case _:
                        msg = f"Unsupported modality: {modality}"
                        raise ValueError(msg)

        return [reference_image] + images


if __name__ == "__main__":  # pragma: no cover
    from rich import print  # noqa: A004
    from tqdm import tqdm  # noqa: A003

    from imgtools.loggers import tqdm_logging_redirect
    # from imgtools.io.readers import read_dicom_auto

    # Example usage
    medinput = SampleInput.build(
        input_directory="data",
        roi_match_map={
            "GTV": ["GTV.*"],
            "Lung": ["Lung.*"],
            "Heart": ["Heart.*"],
            "Esophagus": ["Esophagus.*"],
            "Spinal Cord": ["Spinal Cord.*"],
            "PTV": ["PTV.*"],
        },
        roi_ignore_case=True,
        roi_handling_strategy="merge",
        roi_allow_multi_key_matches=False,
        roi_on_missing_regex=ROIMatchFailurePolicy.WARN,
    )
    print(medinput)

    # print(f"{medinput.crawler!r}")

    # print the tree
    # medinput.print_tree()

    query_string = "*"

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
                result = medinput._load_series(
                    sample=series,
                    load_subseries=False,
                )
            except ValueError as e:
                logger.error(f"Error loading series: {e}")
                continue

    # query_string = "CT,SEG"

    # sample_sets = medinput.interlacer.query(
    #     query_string=query_string,
    #     group_by_root=True,
    # )

    # for series in tqdm(
    #     sample_sets,
    #     desc="Loading series",
    #     unit="series",
    #     leave=False,
    #     total=len(sample_sets),
    # ):
    #     try:
    #         series = medinput._load_series(
    #             sample=series,
    #             load_subseries=False,
    #         )
    #         print(series)
    #     except ValueError as e:
    #         print(f"Error loading series: {e}")
    #         continue
