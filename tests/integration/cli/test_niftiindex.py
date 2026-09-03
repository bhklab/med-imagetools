"""Integration tests for niftiindex: compare crawl index to autopipeline writer index."""

import pytest
from pathlib import Path
from click.testing import CliRunner

import pandas as pd

from imgtools.cli.autopipeline import autopipeline
from imgtools.cli.niftiindex import niftiindex
from imgtools.utils import truncate_uid

# Default autopipeline filename format (must match CLI default for comparison)
AUTOPIPELINE_SCAN_PATTERN = "{SampleNumber}__{PatientID}/{Modality}_{SeriesInstanceUID}/{ImageID}.nii.gz"

# Key columns present in both autopipeline index and nifti crawl index
KEY_COLUMNS = ["SampleNumber", "PatientID", "Modality", "SeriesInstanceUID", "ImageID"]


def _normalize_path(s: str) -> str:
    """Normalize path string for comparison (forward slashes, no leading ./)."""
    if pd.isna(s) or s == "":
        return ""
    return Path(s).as_posix().lstrip("./")


@pytest.fixture(scope="function")
def runner() -> CliRunner:
    return CliRunner()


@pytest.mark.parametrize("collection", ["CPTAC-UCEC"])
def test_niftiindex_matches_autopipeline_index(
    runner: CliRunner,
    tmp_path: Path,
    collection: str,
    DATA_DIR: Path,
):
    """
    Run autopipeline on a DICOM collection, then niftiindex on the NIfTI output.
    Assert the nifti crawl index matches the autopipeline writer index (filepaths + key columns).
    """

    input_dir = DATA_DIR / collection
    if not input_dir.exists():
        pytest.skip(f"Test data directory does not exist: {input_dir}")

    temp_output_dir = tmp_path / "autopipeline_out"
    temp_output_dir.mkdir(parents=True)

    # 1. Run autopipeline (CT only for speed and 1:1 scan rows)
    result = runner.invoke(
        autopipeline,
        [
            str(input_dir),
            str(temp_output_dir),
            "--modalities",
            "CT",
            "--existing-file-mode",
            "overwrite",
            "--jobs",
            "1",
        ],
    )
    assert result.exit_code == 0, f"autopipeline failed: {result.output}"

    autopipeline_index_path = temp_output_dir / f"{temp_output_dir.name}_index.csv"
    assert autopipeline_index_path.exists(), "autopipeline did not write index"
    ap_index = pd.read_csv(autopipeline_index_path)
    assert len(ap_index) >= 1, "autopipeline index has no rows"

    # 2. Run niftiindex on autopipeline output with matching pattern
    result2 = runner.invoke(
        niftiindex,
        [
            "--nifti-dir",
            str(temp_output_dir),
            "--scan-name-pattern",
            AUTOPIPELINE_SCAN_PATTERN,
            "--n-jobs",
            "1",
            "--force",
        ],
    )
    assert result2.exit_code == 0, f"niftiindex failed: {result2.output}"

    # Nifti crawl default: output_dir = nifti_dir.parent / ".imgtools", dataset_name = nifti_dir.name
    nifti_index_path = temp_output_dir.parent / ".imgtools" / temp_output_dir.name / "index.csv"
    assert nifti_index_path.exists(), "niftiindex did not write index"
    nifti_index = pd.read_csv(nifti_index_path)

    # 3. Compare indexes
    ap_paths = set(ap_index["filepath"].astype(str).map(_normalize_path))
    nifti_paths = set(nifti_index["filepath"].astype(str).map(_normalize_path))
    assert ap_paths == nifti_paths, (
        f"filepath set mismatch: autopipeline {len(ap_paths)}, nifti {len(nifti_paths)}"
    )
    assert len(nifti_index) == len(ap_index), (
        f"row count mismatch: autopipeline {len(ap_index)}, nifti {len(nifti_index)}"
    )

    # Compare key columns that exist in both
    for col in KEY_COLUMNS:
        if col not in ap_index.columns or col not in nifti_index.columns:
            continue
        ap_vals = ap_index[col].astype(str).fillna("")
        nifti_vals = nifti_index[col].astype(str).fillna("")

        if col == "SeriesInstanceUID":
            ap_vals = ap_vals.map(truncate_uid) 
            nifti_vals = nifti_vals.map(truncate_uid)
        # Align by filepath
        ap_by_path = dict(zip(ap_index["filepath"].map(_normalize_path), ap_vals))
        nifti_by_path = dict(zip(nifti_index["filepath"].map(_normalize_path), nifti_vals))
        for path in ap_paths:
            assert path in nifti_by_path
            assert ap_by_path[path] == nifti_by_path[path], (
                f"column {col} mismatch at path {path}: "
                f"autopipeline {ap_by_path[path]!r} vs nifti {nifti_by_path[path]!r}"
            )
