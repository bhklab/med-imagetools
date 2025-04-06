from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator

import dpath
import pandas as pd
from tqdm import tqdm

from imgtools.dicom.crawl import parse_dicom_dir
from imgtools.loggers import logger, tqdm_logging_redirect
from dataclasses import fields

__all__ = ["CrawlerSettings", "Crawler"]


@dataclass
class CrawlerSettings:
    """Settings for the DICOM crawler."""

    dicom_dir: Path
    n_jobs: int
    dcm_extension: str = "dcm"
    force: bool = False
    db_json: Path | None = None
    db_csv: Path | None = None
    dataset_name: str | None = None

    def __str__(self) -> str:
        """Return a string representation of the settings."""
        return (
            "CrawlerSettings(\n"
            + "\n".join(
                f"  {f.name}: {getattr(self, f.name)}" for f in fields(self)
            )
            + "\n)"
        )
