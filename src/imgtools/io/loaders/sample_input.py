from __future__ import annotations

import multiprocessing
import os
from pathlib import Path
from typing import Union

from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    field_validator,
    model_validator,
)

from imgtools.coretypes.masktypes.roi_matching import (
    ROIMatcher,
    ROIMatchStrategy,
    Valid_Inputs as ROIMatcherInputs,
    create_roi_matcher,
)
from imgtools.dicom.crawl import Crawler
from imgtools.dicom.interlacer import Interlacer
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
    crawler : Optional[Crawler]
        DICOM crawler instance for processing the input directory.

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
    _crawled: bool = PrivateAttr(default=False, init=False)
    _interlacer: Interlacer | None = PrivateAttr(default=None, init=False)

    def model_post_init(self, __context) -> None:  # noqa: ANN001
        """Initialize the Crawler instance after model initialization."""
        self._crawler = Crawler(
            dicom_dir=self.input_directory,
            dataset_name=self.dataset_name,
            force=self.update_crawl,
            n_jobs=self.n_jobs,
        )

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

    @model_validator(mode="after")
    def set_default_dataset_name(self) -> "SampleInput":
        """Set default dataset name if not provided."""
        if self.dataset_name is None:
            self.dataset_name = self.input_directory.name
            logger.debug(
                f"Using input directory name as dataset name: {self.dataset_name}"
            )

        return self

    @field_validator("modalities")
    @classmethod
    def validate_modalities(cls, v: list[str] | None) -> list[str]:
        """Validate that modalities are a list of strings."""
        if v is None:
            return []

        if not all(isinstance(m, str) for m in v):
            raise ValueError("Modalities must be a list of strings")

        return v

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
        roi_handling_strategy: Union[
            str, ROIMatchStrategy
        ] = ROIMatchStrategy.MERGE,
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

        # Create the ROIMatcher
        roi_matcher = create_roi_matcher(
            roi_match_map,
            ignore_case=roi_ignore_case,
            handling_strategy=roi_handling_strategy,
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

    def crawl(self) -> SampleInput:
        """Run the processing with the current configuration.

        This method is a placeholder for the actual processing logic.
        """
        # Placeholder for processing logic
        logger.info("Running processing with current configuration...")

        self.crawler.crawl()
        self._crawled = True
        return self

    @property
    def interlacer(self) -> Interlacer:
        """Get the Interlacer instance."""
        if not self._crawled:
            raise ValueError("Crawl must be run before querying.")
        if not self._interlacer:
            self._interlacer = Interlacer(crawl_index=self.crawler.index)

        return self._interlacer

    def query(self) -> None:
        self.interlacer.print_tree(input_directory=self.input_directory)


if __name__ == "__main__":  # pragma: no cover
    from rich import print  # noqa: A004

    # Example usage
    medinput = SampleInput.build(
        input_directory="data/NSCLC-Radiomics",
        roi_match_map={
            "GTV": ["GTV.*"],
            "PTV": ["PTV.*"],
        },
        roi_ignore_case=True,
        roi_handling_strategy="merge",
    )
    print(medinput)

    print(f"{medinput.crawler!r}")

    # config.run()
