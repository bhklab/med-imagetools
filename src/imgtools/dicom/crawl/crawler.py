from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from imgtools.dicom.crawl.parse_dicoms import (
    ParseDicomDirResult,
    SeriesMetaMap,
    parse_dicom_dir,
)
from imgtools.loggers import logger, tqdm_logging_redirect

if TYPE_CHECKING:
    from pathlib import Path

    import pandas as pd

__all__ = ["Crawler"]


class CrawlResultsNotAvailableError(Exception):
    """Exception raised when crawler results are accessed before crawling."""

    def __init__(self, method_name: str = "") -> None:
        message = "Crawl results not available. Please run crawl() first."
        if method_name:
            message = f"{message} (Called from: {method_name})"
        super().__init__(message)


class CrawlerOutputDirError(Exception):
    """Exception for errors related to the output directory."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Output directory error: {message}")


@dataclass
class Crawler:
    """Crawl a DICOM directory and extract metadata."""

    dicom_dir: Path
    output_dir: Path | None = None
    dataset_name: str | None = None
    n_jobs: int = 1
    force: bool = False

    _crawl_results: ParseDicomDirResult | None = field(
        init=False, repr=False, default=None
    )

    def crawl(self) -> None:
        """Crawl the DICOM directory and extract metadata."""
        self.output_dir = (
            self.output_dir or self.dicom_dir.parent / ".imgtools"
        )
        validate_output_dir(self.output_dir)

        logger.info(
            "Starting DICOM crawl.",
            dicom_dir=self.dicom_dir,
            output_dir=self.output_dir,
            dataset_name=self.dataset_name,
        )

        with tqdm_logging_redirect():
            crawldb = parse_dicom_dir(
                dicom_dir=self.dicom_dir,
                output_dir=self.output_dir,
                dataset_name=self.dataset_name,
                n_jobs=self.n_jobs,
                force=self.force,
            )
        self._crawl_results = crawldb

    @property
    def crawl_results(self) -> ParseDicomDirResult:
        """Get the crawl results, validating they're available first."""
        if self._crawl_results is None:
            raise CrawlResultsNotAvailableError("crawl_results")
        return self._crawl_results

    def get_series_info(self, series_uid: str) -> dict[str, str]:
        """Get the series information for a given series UID."""
        if series_uid not in self.crawl_results.crawl_db_raw:
            msg = f"Series UID {series_uid} not found in crawl results."
            raise ValueError(msg)

        data = self.crawl_results.crawl_db_raw[series_uid]
        first_subseries = next(iter(data.values()))
        return first_subseries

    def get_folder(self, series_uid: str) -> str:
        """Get the folder for a given series UID."""
        if series_uid not in self.crawl_results.crawl_db_raw:
            msg = f"Series UID {series_uid} not found in crawl results."
            raise ValueError(msg)

        data = self.crawl_results.crawl_db_raw[series_uid]
        first_subseries = next(iter(data.values()))
        return first_subseries["folder"]

    def get_modality(self, series_uid: str) -> str:
        """Get the modality for a given series UID."""
        if series_uid not in self.crawl_results.crawl_db_raw:
            msg = f"Series UID {series_uid} not found in crawl results."
            raise ValueError(msg)

        data = self.crawl_results.crawl_db_raw[series_uid]
        first_subseries = next(iter(data.values()))
        return first_subseries["modality"]

    @property
    def index(self) -> pd.DataFrame:
        """Return the index of the crawl results."""
        return self.crawl_results.index

    @property
    def crawl_db(self) -> list[dict[str, str]]:
        """Return the crawl database."""
        return self.crawl_results.crawl_db

    @property
    def crawl_db_raw(self) -> SeriesMetaMap:
        """Return the crawl database raw."""
        return self.crawl_results.crawl_db_raw

    def __str__(self) -> str:  # pragma: no cover
        """Return a string representation of the crawler."""
        attributes = [
            "dicom_dir",
            "output_dir",
            "dataset_name",
            "n_jobs",
            "force",
        ]
        return (
            "Crawler(\n"
            + "\n".join(
                f"  {attr}: {getattr(self, attr)}" for attr in attributes
            )
            + "\n)"
        )


def validate_output_dir(output_dir: Path) -> None:
    """Validate the output directory."""
    output_dir = output_dir.expanduser().resolve()
    errmsg = ""

    if not output_dir.exists():
        logger.debug(f"Output path {output_dir} does not exist. Creating it.")
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            errmsg = f"Failed to create output directory {output_dir}: {e}"
    elif output_dir.exists() and not output_dir.is_dir():
        errmsg = f"Output path {output_dir} is not a directory."
    elif not os.access(output_dir, os.W_OK):
        # should only get here if the directory exists, but is not writable
        errmsg = f"Output directory {output_dir} is not writable."

        # do some more investigation to give user some more information
        if not os.access(output_dir, os.R_OK):
            errmsg += " It is also not readable."

        # get the owner and permissions of the directory
        try:
            stat_info = output_dir.stat()
            owner = stat_info.st_uid
            permissions = oct(stat_info.st_mode)[-3:]
            errmsg += f" Owner: {owner}, Permissions: {permissions}"
        except OSError as e:
            errmsg += f" Failed to retrieve directory stats for more information: {e}"

    if errmsg:
        raise CrawlerOutputDirError(errmsg)
