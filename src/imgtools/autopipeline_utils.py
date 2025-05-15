"""
Utility functions for the autopipeline module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

# Import Path in type-checking block
from typing import TYPE_CHECKING, Callable, Dict, Generic, List, TypeVar

import pandas as pd

from imgtools.loggers import logger

if TYPE_CHECKING:
    from pathlib import Path

ResultType = TypeVar("ResultType", bound=object)


@dataclass
class PipelineResults(Generic[ResultType]):
    """Class to store and handle pipeline processing results.

    This class stores successful and failed results from processing samples through
    the autopipeline and provides methods for saving reports and generating summary statistics.

    Parameters
    ----------
    successful_results : List[ResultType]
        List of successful processing results
    failed_results : List[ResultType]
        List of failed processing results
    all_results : List[ResultType]
        List of all processing results
    timestamp : str, optional
        Timestamp for this run, by default current datetime
    """

    successful_results: List[ResultType]
    failed_results: List[ResultType]
    all_results: List[ResultType]
    timestamp: str | None = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    @property
    def success_count(self) -> int:
        """Number of successful results."""
        return len(self.successful_results)

    @property
    def failure_count(self) -> int:
        """Number of failed results."""
        return len(self.failed_results)

    @property
    def total_count(self) -> int:
        """Total number of results."""
        return len(self.all_results)

    @property
    def success_rate(self) -> float:
        """Success rate as a percentage."""
        if self.total_count == 0:
            return 0.0
        return (self.success_count / self.total_count) * 100

    def log_summary(self) -> None:
        """Log summary information about the results."""
        logger.info(
            f"Processing complete. {self.success_count} successful, {self.failure_count} failed "
            f"out of {self.total_count} total samples ({self.success_rate:.1f}% success rate)."
        )

    def to_dict(self) -> Dict[str, List[ResultType]]:
        """Convert results to a dictionary."""
        return {
            "success": self.successful_results,
            "failure": self.failed_results,
        }


def save_pipeline_reports(
    results: PipelineResults,
    index_file: "Path",
    root_dir_name: str,
    simplified_columns: List[str],
    index_lock_check_func: Callable[[], "Path"] | None = None,
) -> Dict[str, "Path"]:
    """
    Save pipeline reports including success/failure reports and simplified index.

    Parameters
    ----------
    results : PipelineResults
        The pipeline results to save
    index_file : Path
        Path to the index file
    root_dir_name : str
        Name of the root directory for output
    simplified_columns : List[str]
        List of columns to include in the simplified index
    index_lock_check_func : callable, optional
        Function to check and remove index lock file

    Returns
    -------
    Dict[str, Path]
        Dictionary of saved file paths
    """
    # Log summary
    results.log_summary()

    # Generate report file names
    success_file = index_file.with_name(
        f"{root_dir_name}_successful_{results.timestamp}.json"
    )
    failure_file = index_file.with_name(
        f"{root_dir_name}_failed_{results.timestamp}.json"
    )

    # Write simplified index file
    simple_index = index_file.parent / f"{index_file.stem}-simple.csv"

    try:
        index_df = pd.read_csv(index_file)

        # Get columns in the order we want
        # If a column is not in the index_df, it will be filled with NaN
        index_df = index_df[simplified_columns]

        # Sort by 'filepath' to make it easier to read
        if "filepath" in index_df.columns:
            index_df = index_df.sort_values(by=["filepath"])

        index_df.to_csv(simple_index, index=False)
        logger.info(f"Index file saved to {simple_index}")
    except Exception as e:
        logger.error(f"Failed to create simplified index: {e}")

    # Remove lockfile if a function was provided
    # TODO:: probably a better way to do this
    if index_lock_check_func is not None:
        lock_file = index_lock_check_func()
        if lock_file is not None and lock_file.exists():
            lock_file.unlink()
            logger.debug(f"Lock file removed: {lock_file}")

    # Convert results to dictionaries for JSON serialization
    success_dicts = [result.to_dict() for result in results.successful_results]

    # Write success report
    with success_file.open("w", encoding="utf-8") as f:
        json.dump(success_dicts, f, indent=2)
    logger.info(f"Detailed success report saved to {success_file}")

    saved_files = {"success_file": success_file, "simple_index": simple_index}

    # If no failures, we can skip writing the failure file
    if results.failure_count == 0:
        return saved_files

    # Write failure report
    failure_dicts = [result.to_dict() for result in results.failed_results]
    with failure_file.open("w", encoding="utf-8") as f:
        json.dump(failure_dicts, f, indent=2)
    logger.info(f"Detailed failure report saved to {failure_file}")

    saved_files["failure_file"] = failure_file
    return saved_files
