from __future__ import annotations

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

# ParseDicomDirResult = t.NamedTuple(
#     "ParseDicomDirResult",
#     [
#         ("crawl_db", list[dict[str, str]]),
#         ("index", pd.DataFrame),
#         ("crawl_db_raw", SeriesMetaMap),
#         ("crawl_db_path", pathlib.Path),
#         ("index_csv_path", pathlib.Path),
#         ("crawl_cache_path", pathlib.Path),
#         ("sop_map_path", pathlib.Path),
#     ],
# )


@dataclass
class Crawler:
    """Crawl a DICOM directory and extract metadata."""

    dicom_dir: Path
    output_dir: Path | None = None
    dataset_name: str | None = None
    n_jobs: int = 1
    force: bool = False

    crawl_results: ParseDicomDirResult = field(init=False, repr=False)

    def crawl(self) -> None:
        """Crawl the DICOM directory and extract metadata."""
        self.output_dir = (
            self.output_dir or self.dicom_dir.parent / ".imgtools"
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

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
        self.crawl_results = crawldb

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

    def __str__(self) -> str:
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
