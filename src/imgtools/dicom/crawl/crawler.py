from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Generator

import dpath
import pandas as pd
from tqdm import tqdm

from imgtools.dicom.crawl import ParseDicomDirResult, parse_dicom_dir
from imgtools.loggers import logger, tqdm_logging_redirect
import click

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


@click.command()
@click.option(
    "--dicom-dir",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to the DICOM directory.",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to the output directory. If not specified, a directory named '.imgtools' will be created in the parent directory of the DICOM directory.",
)
@click.option(
    "--dataset-name",
    type=str,
    default=None,
    help="Name of the dataset. If not specified, the name of the DICOM directory will be used.",
)
@click.option(
    "--n-jobs",
    type=int,
    default=1,
    help="Number of jobs to use for parallel processing.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Force overwrite existing files.",
)
@click.option(
    "--dcm-extension",
    type=str,
    default="dcm",
    help="DICOM file extension.",
)
def index(
    dicom_dir: Path,
    output_dir: Path | None,
    dataset_name: str | None,
    n_jobs: int,
    force: bool,
    dcm_extension: str,
) -> None:
    """Create CrawlerSettings from command line arguments."""
    settings = CrawlerSettings(
        dicom_dir=dicom_dir,
        output_dir=output_dir,
        dataset_name=dataset_name,
        n_jobs=n_jobs,
        force=force,
        dcm_extension=dcm_extension,
    )
    crawler = Crawler(settings=settings)

    logger.info("Crawling completed.")
    logger.info("Crawl results saved to %s", crawler.settings.output_dir)


if __name__ == "__main__":
    index()

    # settings = CrawlerSettings(
    #     dicom_dir=Path("data/Head-Neck-PET-CT"),
    #     output_dir=None,  # let the function create a new folder
    #     dataset_name=None,  # determined by folder name
    #     n_jobs=4,
    #     force=False,
    # )

    # crawler = Crawler(settings=settings)
