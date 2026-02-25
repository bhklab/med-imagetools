from __future__ import annotations

import json
import re
import typing as t
from pathlib import Path

import numpy as np
import pandas as pd
import SimpleITK as sitk
from joblib import Parallel, delayed  # type: ignore
from tqdm import tqdm

from imgtools.coretypes import Mask, MedImage
from imgtools.loggers import logger

# ---------------------------------------------------------------------------
# Public constants and types
# ---------------------------------------------------------------------------

NIFTI_EXTENSIONS = (".nii.gz", ".nii")
MetadataInput = t.Union[str, Path, list[t.Union[str, Path]]]

# ---------------------------------------------------------------------------
# Exceptions and result types
# ---------------------------------------------------------------------------


class MetadataJoinColumnError(ValueError):
    """Raised when metadata_join_col is missing or invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Metadata join column error: {message}")


class ParseNiftiDirResult(
    t.NamedTuple(
        "ParseNiftiDirResult",
        [
            ("index", pd.DataFrame),
            ("index_csv_path", Path),
            ("crawl_cache_path", Path),
            ("unmatched_files", list[str]),
            ("extensions", tuple[str, ...]),
            ("deep", bool),
            ("metadata_path", list[Path]),
            ("metadata_join_col", str | None),
        ],
    ),
):
    """Result of parsing a directory: index DataFrame, paths to index/cache, and unmatched file list."""

    __slots__ = ()


# ---------------------------------------------------------------------------
# Pattern matching: template string -> regex
# ---------------------------------------------------------------------------

PLACEHOLDER_RE = re.compile(r"\{(\w+)(?::(\w+))?\}")
_TYPE_REGEX: dict[str, str] = {"d": r"\d+"}
_TYPE_NORMALIZERS: dict[str, t.Callable[[str], str]] = {
    "d": lambda v: str(int(v)),
}


def _pattern_to_regex(
    pattern: str,
) -> tuple[re.Pattern[str], list[str], dict[str, t.Callable[[str], str]]]:
    """Convert a ``{Key}`` or ``{Key:type}`` template into a compiled regex with named groups."""
    parts = PLACEHOLDER_RE.split(pattern)
    keys: list[str] = []
    normalizers: dict[str, t.Callable[[str], str]] = {}
    regex_parts: list[str] = []
    for i, part in enumerate(parts):
        mod = i % 3
        if mod == 0:
            regex_parts.append(re.escape(part))
        elif mod == 1:
            keys.append(part)
        else:
            key = keys[-1]
            capture_re = _TYPE_REGEX.get(part, "[^/]+") if part else "[^/]+"
            regex_parts.append(f"(?P<{key}>{capture_re})")
            if part and part in _TYPE_NORMALIZERS:
                normalizers[key] = _TYPE_NORMALIZERS[part]
    return re.compile("^" + "".join(regex_parts) + "$"), keys, normalizers


def _apply_normalizers(
    groups: dict[str, str],
    normalizers: dict[str, t.Callable[[str], str]],
) -> dict[str, str]:
    """Apply normaliser functions to matching groups where defined."""
    return {
        k: normalizers[k](v) if k in normalizers else v
        for k, v in groups.items()
    }


def _match_file(
    rel_path: str,
    scan_regex: re.Pattern[str] | None,
    scan_normalizers: dict[str, t.Callable[[str], str]],
    mask_regex: re.Pattern[str] | None,
    mask_normalizers: dict[str, t.Callable[[str], str]],
) -> tuple[dict[str, str], str] | None:
    """Match rel_path against scan then mask regex. Returns (groupdict, file_type) or None.

    Patterns are anchored: the full path must match from start to end (no partial matches).
    """
    if scan_regex is not None:
        m = scan_regex.fullmatch(rel_path)
        if m:
            return _apply_normalizers(m.groupdict(), scan_normalizers), "scan"
    if mask_regex is not None:
        m = mask_regex.fullmatch(rel_path)
        if m:
            return _apply_normalizers(m.groupdict(), mask_normalizers), "mask"
    return None


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


def _normalise_extensions(
    extensions: str | list[str] | None,
) -> tuple[str, ...]:
    """Coerce extensions into a tuple of dot-prefixed strings."""
    if extensions is None:
        return NIFTI_EXTENSIONS
    if isinstance(extensions, str):
        extensions = [extensions]
    return tuple(
        ext if ext.startswith(".") else f".{ext}" for ext in extensions
    )


def find_niftis(
    directory: Path,
    extensions: tuple[str, ...] = NIFTI_EXTENSIONS,
) -> list[Path]:
    """Recursively find all files under directory matching the given extensions."""
    files: list[Path] = []
    for ext in extensions:
        files.extend(directory.rglob(f"*{ext}"))
    return sorted(files)


# ---------------------------------------------------------------------------
# Validation and logging
# ---------------------------------------------------------------------------


def _validate_join_col_in_patterns(
    metadata_join_col: str,
    scan_keys: list[str],
    mask_keys: list[str] | None,
) -> None:
    """Raise if metadata_join_col is not a placeholder in the patterns."""
    missing_in: list[str] = []
    if metadata_join_col not in scan_keys:
        missing_in.append("scan_name_pattern")
    if mask_keys is not None and metadata_join_col not in mask_keys:
        missing_in.append("mask_name_pattern")
    if missing_in:
        msg = (
            f"metadata_join_col={metadata_join_col!r} must appear as a "
            f"{{placeholder}} in {', '.join(missing_in)}."
        )
        raise MetadataJoinColumnError(msg)


def _log_unmatched_summary(
    unmatched: list[str],
    total: int,
    scan_pattern: str,
    mask_pattern: str | None,
) -> None:
    """Log a warning summarising unmatched files."""
    patterns_tried = [scan_pattern]
    if mask_pattern is not None:
        patterns_tried.append(mask_pattern)
    logger.warning(
        "Some files did not match any pattern.",
        unmatched_count=len(unmatched),
        total_count=total,
        example_paths=unmatched[:5],
        patterns_tried=patterns_tried,
        hint="Check that patterns include all path segments between root and filename.",
    )


# ---------------------------------------------------------------------------
# Per-file introspection
# ---------------------------------------------------------------------------


def _introspect(
    fpath: Path,
    file_type: str,
) -> dict[str, t.Any]:
    extra: dict[str, t.Any] = {}
    """Read one image and return a serialized fingerprint payload."""  

    sitk_img = sitk.ReadImage(str(fpath))

    if file_type == "scan":
        img = MedImage(sitk_img)
    elif file_type == "mask":
        arr = sitk.GetArrayFromImage(sitk_img)

        if np.count_nonzero(arr) == 0:
            logger.warning(f"Mask {fpath} is empty.")
            img = MedImage(sitk_img)
        else:
            arr[arr > 0] = 1
            _sitk_img = sitk.GetImageFromArray(arr)
            _sitk_img.CopyInformation(sitk_img)
            img = Mask(_sitk_img, metadata={})

    extra.update(img.serialized_fingerprint)

    return extra


def _process_one_nifti(
    fpath: Path,
    nifti_dir: Path,
    scan_regex: re.Pattern[str],
    scan_normalizers: dict[str, t.Callable[[str], str]],
    mask_regex: re.Pattern[str] | None,
    mask_normalizers: dict[str, t.Callable[[str], str]],
    all_keys: list[str],
    deep: bool,
) -> tuple[dict[str, t.Any] | None, str]:
    """Process one NIfTI file: match pattern and introspect. For use in parallel processing.

    Returns
    -------
    (record, rel_path) : record is None if file did not match any pattern; rel_path is always the relative path.
    """
    rel = fpath.relative_to(nifti_dir).as_posix()
    result = _match_file(
        rel, scan_regex, scan_normalizers, mask_regex, mask_normalizers
    )
    if result is None:
        return None, rel
    groups, file_type = result
    record: dict[str, t.Any] = {k: groups.get(k, "") for k in all_keys}
    record["filepath"] = rel
    record["file_type"] = file_type
    if deep:
        try:
            record.update(_introspect(fpath, file_type))
        except Exception as e:
            logger.error(f"Error reading image {fpath}: {e}")
    return record, rel


# ---------------------------------------------------------------------------
# Metadata I/O
# ---------------------------------------------------------------------------


def _normalise_metadata_paths(
    metadata_path: MetadataInput | None,
) -> list[Path]:
    """Coerce metadata_path (str, Path, or list) into a list of Paths."""
    if metadata_path is None:
        return []
    if isinstance(metadata_path, (str, Path)):
        return [Path(metadata_path)]
    return [Path(p) for p in metadata_path]


def _read_metadata_file(metadata_path: Path) -> pd.DataFrame:
    """Read a CSV or JSON metadata file into a DataFrame."""
    suffix = metadata_path.suffix.lower()
    if suffix == ".json":
        data = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
        if isinstance(data, list):
            return pd.DataFrame(data)
        if isinstance(data, dict):
            return pd.DataFrame([data])
        msg = f"Unsupported JSON structure in {metadata_path}"
        raise ValueError(msg)
    return pd.read_csv(
        metadata_path, sep=None, engine="python", encoding="utf-8-sig"
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def parse_nifti_dir(  # noqa: PLR0912, PLR0915
    nifti_dir: Path,
    scan_name_pattern: str,
    mask_name_pattern: str | None,
    output_dir: Path,
    dataset_name: str | None,
    force: bool,
    extensions: str | list[str] | None = None,
    deep: bool = False,
    metadata_path: MetadataInput | None = None,
    metadata_join_col: str | None = None,
    n_jobs: int = -1,
) -> ParseNiftiDirResult:
    """Parse a directory of image files and build an index of matched scan/mask pairs.

    Parameters
    ----------
    nifti_dir
        Root directory containing image files.
    scan_name_pattern
        Template for scan paths, e.g. ``"{PatientID}/{Modality}.nii.gz"``.
    mask_name_pattern
        Optional template for mask paths, e.g. ``"{PatientID}/segmentations/{ROI}.nii.gz"``.
    output_dir
        Directory where index and cache are written.
    dataset_name
        Subdir name under output_dir; defaults to nifti_dir.name.
    force
        If True, ignore cache and re-crawl.
    extensions
        File extension(s) to search. Single string or list; default NIfTI.
    deep
        If True, read each image and run _introspect (fingerprint). If False, only file-level metadata.
    metadata_path
        Path(s) to CSV/JSON to merge into the index.
    metadata_join_col
        Column that must be a {placeholder} in patterns and in each metadata file. Required if metadata_path set.
    n_jobs
        Number of parallel jobs for introspecting files. -1 uses all available cores.

    Returns
    -------
    ParseNiftiDirResult
        NamedTuple with: index, index_csv_path, crawl_cache_path, unmatched_files,
        extensions, deep, metadata_path, metadata_join_col.

    Raises
    ------
    FileNotFoundError
        If nifti_dir does not exist or no matching files found.
    MetadataJoinColumnError
        If metadata_join_col is missing or invalid.
    ValueError
        If all files are unmatched.
    """
    metadata_paths = _normalise_metadata_paths(metadata_path)
    if metadata_paths and metadata_join_col is None:
        raise MetadataJoinColumnError(
            "metadata_join_col is required when metadata_path is given."
        )

    nifti_dir = nifti_dir.resolve()
    if not nifti_dir.is_dir():
        msg = f"Directory does not exist: {nifti_dir}"
        raise FileNotFoundError(msg)

    dataset_name = dataset_name or nifti_dir.name
    out_root = output_dir / dataset_name
    out_root.mkdir(parents=True, exist_ok=True)
    index_csv_path = out_root / "index.csv"
    crawl_cache_path = out_root / "crawl_cache.json"

    # Use cache if available
    if not force and index_csv_path.exists() and crawl_cache_path.exists():
        logger.info(
            "Loading cached crawl results.", index_csv_path=str(index_csv_path)
        )
        index = pd.read_csv(index_csv_path)
        cache = json.loads(crawl_cache_path.read_text())
        return ParseNiftiDirResult(
            index=index,
            index_csv_path=index_csv_path,
            crawl_cache_path=crawl_cache_path,
            unmatched_files=cache.get("unmatched_files", []),
            extensions=tuple(cache.get("extensions", list(NIFTI_EXTENSIONS))),
            deep=cache.get("deep", deep),
            metadata_path=[Path(p) for p in cache.get("metadata_path", [])],
            metadata_join_col=cache.get("metadata_join_col"),
        )

    # Discover files
    resolved_extensions = _normalise_extensions(extensions)
    nifti_files = find_niftis(nifti_dir, extensions=resolved_extensions)
    logger.info(f"Found {len(nifti_files)} NIfTI files in {nifti_dir}.")
    if not nifti_files:
        msg = f"No matching files in {nifti_dir}"
        raise FileNotFoundError(msg)

    # Compile patterns
    scan_regex, scan_keys, scan_normalizers = _pattern_to_regex(
        scan_name_pattern
    )
    mask_regex: re.Pattern[str] | None = None
    mask_keys: list[str] = []
    mask_normalizers: dict[str, t.Callable[[str], str]] = {}
    if mask_name_pattern is not None:
        mask_regex, mask_keys, mask_normalizers = _pattern_to_regex(
            mask_name_pattern
        )
    all_keys = list(dict.fromkeys(scan_keys + mask_keys))
    if metadata_join_col is not None:
        _validate_join_col_in_patterns(
            metadata_join_col,
            scan_keys,
            mask_keys if mask_name_pattern else None,
        )

    # Match and introspect each file in parallel
    records: list[dict[str, t.Any]] = []
    unmatched: list[str] = []
    description = f"Parsing {len(nifti_files)} files"

    for rec, rel in Parallel(n_jobs=n_jobs, return_as="generator")(
        delayed(_process_one_nifti)(
            fpath,
            nifti_dir,
            scan_regex,
            scan_normalizers,
            mask_regex,
            mask_normalizers,
            all_keys,
            deep,
        )
        for fpath in tqdm(
            nifti_files,
            desc=description,
            mininterval=1,
            leave=False,
            colour="green",
        )
    ):
        if rec is None:
            unmatched.append(rel)
        else:
            records.append(rec)

    if unmatched:
        _log_unmatched_summary(
            unmatched, len(nifti_files), scan_name_pattern, mask_name_pattern
        )
    if not records:
        msg = (
            f"All {len(nifti_files)} files were unmatched. "
            f"Check scan_name_pattern and mask_name_pattern."
        )
        raise ValueError(msg)

    index = pd.DataFrame.from_records(records)

    # Merge external metadata
    for mpath in metadata_paths:
        meta = _read_metadata_file(mpath)
        if metadata_join_col not in meta.columns:
            msg = f"metadata_join_col={metadata_join_col!r} not in {mpath.name}: {list(meta.columns)}"
            raise MetadataJoinColumnError(msg)
        meta[metadata_join_col] = meta[metadata_join_col].astype(str)
        index = index.merge(meta, on=metadata_join_col, how="left")
        logger.info(
            "Merged metadata.",
            metadata_path=str(mpath),
            join_col=metadata_join_col,
        )

    index.to_csv(index_csv_path, index=False)
    logger.info("Saved index.", path=str(index_csv_path), rows=len(index))

    crawl_cache_path.write_text(
        json.dumps(
            {
                "nifti_dir": str(nifti_dir),
                "scan_name_pattern": scan_name_pattern,
                "mask_name_pattern": mask_name_pattern,
                "unmatched_files": unmatched,
                "extensions": list(resolved_extensions),
                "deep": deep,
                "metadata_path": list(str(p) for p in metadata_paths),
                "metadata_join_col": metadata_join_col,
            },
            indent=2,
        )
    )

    return ParseNiftiDirResult(
        index=index,
        index_csv_path=index_csv_path,
        crawl_cache_path=crawl_cache_path,
        unmatched_files=unmatched,
        extensions=resolved_extensions,
        deep=deep,
        metadata_path=metadata_paths,
        metadata_join_col=metadata_join_col,
    )
