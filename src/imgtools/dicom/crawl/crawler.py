from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING

from imgtools.dicom.crawl.parse_dicoms import (
    ParseDicomDirResult,
    parse_dicom_dir,
)
from imgtools.loggers import logger, tqdm_logging_redirect

if TYPE_CHECKING:
    from pathlib import Path

    import pandas as pd

__all__ = ["CrawlerSettings", "Crawler"]


@dataclass
class CrawlerSettings:
    """Settings for the DICOM crawler."""

    dicom_dir: Path
    output_dir: Path | None = None
    dataset_name: str | None = None
    n_jobs: int = 1
    force: bool = False
    dcm_extension: str = "dcm"

    def __str__(self) -> str:
        """Return a string representation of the settings."""
        return (
            "CrawlerSettings(\n"
            + "\n".join(
                f"  {f.name}: {getattr(self, f.name)}" for f in fields(self)
            )
            + "\n)"
        )


@dataclass
class Crawler:
    """Crawl a DICOM directory and extract metadata."""

    settings: CrawlerSettings

    crawl_results: ParseDicomDirResult = field(init=False)
    index: pd.DataFrame = field(init=False)

    def __post_init__(self) -> None:
        """Crawl the DICOM directory and extract metadata."""
        self.settings.output_dir = (
            self.settings.output_dir
            or self.settings.dicom_dir.parent / ".imgtools"
        )
        self.settings.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Starting DICOM crawl.",
            dicom_dir=self.settings.dicom_dir,
            output_dir=self.settings.output_dir,
            dataset_name=self.settings.dataset_name,
        )
        crawldb: ParseDicomDirResult

        with tqdm_logging_redirect():
            crawldb = parse_dicom_dir(
                dicom_dir=self.settings.dicom_dir,
                output_dir=self.settings.output_dir,
                dataset_name=self.settings.dataset_name,
                extension=self.settings.dcm_extension,
                n_jobs=self.settings.n_jobs,
                force=self.settings.force,
            )
        self.crawl_results = crawldb
