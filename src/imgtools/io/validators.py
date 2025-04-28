"""Validators for the SampleInput and related classes."""

from __future__ import annotations

import multiprocessing
import os
from pathlib import Path

from imgtools.loggers import logger


def validate_directory(v: str | Path, create: bool = False) -> Path:
    """Validate that the input directory exists and is readable."""
    path = Path(v) if not isinstance(v, Path) else v

    if not path.exists():
        if create:
            try:
                path.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                msg = f"Failed to create directory: {path} ({e})"
                raise ValueError(msg) from e
        else:
            msg = f"Directory does not exist: {path}"
            raise ValueError(msg)

    if not path.is_dir():
        msg = f"Path must be a directory: {path}"
        raise ValueError(msg)

    if not os.access(path, os.R_OK):
        msg = f"Directory is not readable {path}"
        raise ValueError(msg)

    return path


def validate_n_jobs(v: int) -> int:
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


def validate_modalities(v: list[str] | None) -> list[str] | None:
    """Validate that modalities are a list of strings."""
    if v is None:
        return v

    if not all(isinstance(m, str) for m in v):
        raise ValueError("Modalities must be a list of strings")

    return v
