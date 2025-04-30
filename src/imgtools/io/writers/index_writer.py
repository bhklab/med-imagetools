from __future__ import annotations

import csv
from typing import TYPE_CHECKING, Any

from fasteners import InterProcessLock  # type: ignore

if TYPE_CHECKING:
    from pathlib import Path


class IndexWriterError(Exception):
    """
    Base exception for all IndexWriter-related errors.

    This should be used to catch any general IndexWriter failure
    that does not fall under a more specific error type.
    """

    pass


class IndexSchemaMismatchError(IndexWriterError):
    """
    Raised when the index file schema is missing required fields
    and merging columns is disabled.

    Use this error to notify the caller that the existing index
    cannot accommodate the current row’s structure and merging
    is not allowed.
    """

    def __init__(self, missing_fields: set[str], index_path: Path) -> None:
        self.missing_fields = missing_fields
        self.index_path = index_path
        msg = (
            f"Schema mismatch in index file '{index_path}'. "
            f"Missing fields: {sorted(missing_fields)}. "
            "Set merge_columns=True to allow schema evolution."
        )
        super().__init__(msg)


class IndexReadError(IndexWriterError):
    """
    Raised when reading the index file fails unexpectedly.

    Use this when an exception occurs while attempting to read
    or parse the existing CSV file.
    """

    def __init__(
        self, index_path: Path, original_exception: Exception
    ) -> None:
        self.index_path = index_path
        self.original_exception = original_exception
        msg = f"Failed to read index file '{index_path}': {original_exception}"
        super().__init__(msg)


class IndexWriteError(IndexWriterError):
    """
    Raised when writing to the index file fails unexpectedly.

    Use this when a CSV write operation fails during append
    or full rewrite of the index.
    """

    def __init__(
        self, index_path: Path, original_exception: Exception
    ) -> None:
        self.index_path = index_path
        self.original_exception = original_exception
        msg = f"Failed to write to index file '{index_path}': {original_exception}"
        super().__init__(msg)


class IndexWriter:
    """Handles safe and smart updates to a shared CSV file used as an index.

    This class manages writing entries to a CSV index while avoiding problems
    like file corruption (from two writers editing at once), column mismatches,
    or missing data.

    Think of this like a notebook where many writers might want to write down
    their output paths and metadata. This class is the referee: it waits for its
    turn (locking), makes sure the notebook has the right columns, and writes
    everything in order.
    """

    def __init__(
        self, index_path: Path, lock_path: Path | None = None
    ) -> None:
        """
        Parameters
        ----------
        index_path : Path
            Path to the CSV file that acts as a shared index.
        lock_path : Path | None, optional
            Path to a `.lock` file that ensures one writer updates at a time.
                If None, uses the index file path with `.lock` added.
        """
        self.index_path: Path = index_path
        self.lock_path: Path = lock_path or index_path.with_suffix(
            index_path.suffix + ".lock"
        )

    def write_entry(
        self,
        path: Path,
        context: dict[str, Any],
        filepath_column: str = "path",
        replace_existing: bool = False,
        merge_columns: bool = True,
    ) -> None:
        """Write one entry to the index file. Safe in parallel with full lock.

        You give this a path and a dictionary of info.
        → It checks the index file.
        → If the path is already in there and you want to replace it, it does.
        → If your new info has different keys, it adds new columns (if allowed).
        → Then it saves the full table back to disk, safely.

        Parameters
        ----------
        path : Path
            The file path that you want to record in the index.
        context : dict[str, Any]
            Extra metadata (e.g. subject ID, date, label) to log alongside the path.
        filepath_column : str, default="path"
            Name of the column to store the file path. Default is "path".
        replace_existing : bool, default=False
            If True, update the row if one with the same path already exists.
        merge_columns : bool, default=True
            If True, automatically add new columns if the context has fields the
                CSV didn't have yet.

        Raises
        ------
        IndexSchemaMismatchError
            If the new entry's schema doesn't match the existing one and
            merging is not allowed.
        IndexReadError
            If there are issues reading the existing index file.
        IndexWriteError
            If there are issues writing to the index file.
        """
        entry = {
            filepath_column: str(path),
            **{k: str(v) for k, v in context.items()},
        }

        with InterProcessLock(self.lock_path):
            try:
                existing_rows, existing_fieldnames = self._read_existing_rows(
                    filepath_column, replace_existing, entry
                )
            except OSError as e:
                raise IndexReadError(self.index_path, e) from e

            try:
                final_fieldnames = self._validate_or_merge_schema(
                    existing_fieldnames, set(entry.keys()), merge_columns
                )
            except IndexSchemaMismatchError:
                raise

            all_rows = self._normalize_rows(
                existing_rows + [entry], final_fieldnames
            )

            try:
                self._write_rows(all_rows, final_fieldnames)
            except Exception as e:
                raise IndexWriteError(self.index_path, e) from e

    def _read_existing_rows(
        self,
        filepath_column: str,
        replace_existing: bool,
        entry: dict[str, str],
    ) -> tuple[list[dict[str, str]], list[str]]:
        """Read the index file and optionally filter out old versions of this entry.

        If the path of the entry we're about to write already exists in the CSV,
        we remove it from the new list of rows to write. This avoids duplicates.

        Returns
        -------
        rows : list of dict[str, str]
            Existing rows (minus the old one if we're replacing it).
        fieldnames : list of str
            The existing column names in the CSV file.
        """
        if not self.index_path.exists():
            return [], []

        with self.index_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_fieldnames = list(reader.fieldnames or [])

            rows = []
            for row in reader:
                if (
                    replace_existing
                    and row.get(filepath_column) == entry[filepath_column]
                ):
                    continue
                rows.append(row)

        return rows, existing_fieldnames

    def _validate_or_merge_schema(
        self,
        existing_fieldnames: list[str],
        new_fieldnames: set[str],
        merge_columns: bool,
    ) -> list[str]:
        """
        Check if new columns match the existing ones, or merge if allowed.

        If the new data has keys that weren’t in the CSV, we either:
        - Throw an error (if merging is off), or
        - Add the new columns so everything can fit (if merging is on).

        Returns
        -------
        final_fieldnames : list of str
            The full list of column headers to use in the output.

        """
        existing_set = set(existing_fieldnames)
        if not existing_set:
            return sorted(new_fieldnames)

        if merge_columns:
            return sorted(existing_set | new_fieldnames)

        missing = new_fieldnames - existing_set
        if missing:
            raise IndexSchemaMismatchError(
                missing_fields=missing, index_path=self.index_path
            )

        return existing_fieldnames

    def _normalize_rows(
        self, rows: list[dict[str, str]], fieldnames: list[str]
    ) -> list[dict[str, str]]:
        """
        Ensure every row has all the columns, using "" for missing values.

        Returns
        -------
        rows : list of dict[str, str]
            All rows padded to match the final fieldnames.
        """
        return [{key: row.get(key, "") for key in fieldnames} for row in rows]

    def _write_rows(
        self, rows: list[dict[str, str]], fieldnames: list[str]
    ) -> None:
        """
        Write the full table back to disk.

        This is the final save step. We write everything out
        so it's clean and consistent for the next user.
        """
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

        with self.index_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":  # pragma: no cover
    import random
    import shutil
    from datetime import datetime
    from pathlib import Path

    # perf timer
    from time import perf_counter as timer

    from joblib import Parallel, delayed  # type: ignore

    # Setup shared index path
    INDEX_PATH = Path("example_outputs/index.csv")
    if INDEX_PATH.exists():
        shutil.move(INDEX_PATH, INDEX_PATH.with_suffix(".bak"))
    # Create a global IndexWriter instance
    writer = IndexWriter(index_path=INDEX_PATH)

    def generate_context(i: int) -> dict[str, Any]:
        """Create fake metadata for the ith file."""
        return {
            "subject_id": f"subject_{i % 10}",
            "modality": random.choice(["CT", "MR", "SEG"]),
            "timestamp": datetime.now().isoformat(),
            "quality_score": round(random.uniform(0, 1), 3),
        }

    def write_entry(i: int) -> None:
        """Each parallel worker writes a unique path and context to the index."""
        output_path = Path(f"output/fake_file_{i}.nii.gz")
        context = generate_context(i)

        # Use a new IndexWriter per process to avoid shared state
        local_writer = IndexWriter(index_path=INDEX_PATH)
        local_writer.write_entry(path=output_path, context=context)

    start_time = timer()
    print(f"✔ Index writing started at: {INDEX_PATH.resolve()}")  # noqa

    # Use 12 parallel workers to write 1000 entries
    Parallel(n_jobs=12)(delayed(write_entry)(i) for i in range(1000))

    print(f"✔ Index writing complete at: {INDEX_PATH.resolve()}")  # noqa

    end_time = timer()
    elapsed_time = end_time - start_time
    print(f"✔ Total time taken: {elapsed_time:.2f} seconds")  # noqa
