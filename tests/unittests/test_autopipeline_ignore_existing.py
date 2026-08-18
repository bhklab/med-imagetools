"""Tests for ignoring samples with existing writer output."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from imgtools.autopipeline_utils import filter_samples_without_existing_output
from imgtools.io.sample_output import DEFAULT_FILENAME_FORMAT
from imgtools.io.writers import ExistingFileMode, NIFTIWriter
from imgtools.utils import sanitize_file_name, truncate_uid


def _sample(
    patient_id: str,
    *,
    modality: str = "CT",
    series_uid: str = "1.2.3",
    study_uid: str = "1.2.4",
):
    return [
        SimpleNamespace(
            PatientID=patient_id,
            Modality=modality,
            SeriesInstanceUID=series_uid,
            StudyInstanceUID=study_uid,
            ReferencedSeriesUID=None,
        )
    ]


def _writer(
    tmp_path: Path,
    filename_format: str = DEFAULT_FILENAME_FORMAT,
    *,
    sanitize_filenames: bool = True,
    truncate_uids_in_filename: int = 8,
) -> NIFTIWriter:
    return NIFTIWriter(
        root_directory=tmp_path,
        filename_format=filename_format,
        existing_file_mode=ExistingFileMode.OVERWRITE,
        create_dirs=True,
        sanitize_filenames=sanitize_filenames,
        truncate_uids_in_filename=truncate_uids_in_filename,
    )


def test_filter_skips_existing_nested_sample(tmp_path: Path) -> None:
    writer = _writer(tmp_path)
    samples = [_sample("Patient_A"), _sample("Patient_B"), _sample("Patient_C")]

    existing = tmp_path / "0001__Patient_B"
    existing.mkdir()
    (existing / "marker.txt").write_text("done")

    kept, skipped = filter_samples_without_existing_output(samples, writer)

    assert [number for number, _ in kept] == ["0000", "0002"]
    assert [sample[0].PatientID for _, sample in kept] == [
        "Patient_A",
        "Patient_C",
    ]
    assert skipped == ["0001"]


def test_filter_skips_existing_patient_format(tmp_path: Path) -> None:
    writer = _writer(tmp_path, "{PatientID}/{Modality}/{ImageID}.nii.gz")
    samples = [_sample("Patient_A"), _sample("Patient_B")]

    patient_dir = tmp_path / "Patient_A"
    patient_dir.mkdir()
    (patient_dir / "CT").mkdir()
    (patient_dir / "CT" / "CT.nii.gz").write_text("x")

    kept, skipped = filter_samples_without_existing_output(samples, writer)

    assert [sample[0].PatientID for _, sample in kept] == ["Patient_B"]
    assert skipped == ["0000"]


def test_filter_skips_existing_flat_format(tmp_path: Path) -> None:
    writer = _writer(tmp_path, "{PatientID}_{Modality}.nii.gz")
    samples = [_sample("Patient_C"), _sample("Patient_D")]

    (tmp_path / "Patient_C_CT.nii.gz").write_text("x")

    kept, skipped = filter_samples_without_existing_output(samples, writer)

    assert [sample[0].PatientID for _, sample in kept] == ["Patient_D"]
    assert skipped == ["0000"]


def test_filter_keeps_all_when_no_existing_output(tmp_path: Path) -> None:
    writer = _writer(tmp_path)
    samples = [_sample("Patient_A"), _sample("Patient_B")]

    kept, skipped = filter_samples_without_existing_output(samples, writer)

    assert len(kept) == 2
    assert skipped == []


def test_filter_skips_after_filename_sanitization(tmp_path: Path) -> None:
    writer = _writer(tmp_path, "{PatientID}/{Modality}.nii.gz")
    patient_id = "Patient With Spaces"
    samples = [_sample(patient_id), _sample("Other")]

    sanitized = sanitize_file_name(patient_id)
    sample_dir = tmp_path / sanitized
    sample_dir.mkdir()
    (sample_dir / "CT.nii.gz").write_text("x")

    kept, skipped = filter_samples_without_existing_output(samples, writer)

    assert [sample[0].PatientID for _, sample in kept] == ["Other"]
    assert skipped == ["0000"]


def test_filter_skips_after_uid_truncation(tmp_path: Path) -> None:
    series_uid = "1.2.840.10008.1.2.1.9876543210"
    writer = _writer(
        tmp_path,
        "{SeriesInstanceUID}.nii.gz",
        truncate_uids_in_filename=8,
    )
    samples = [
        _sample("Patient_A", series_uid=series_uid),
        _sample("Patient_B", series_uid="9.9.9.9999999999"),
    ]

    truncated = truncate_uid(series_uid, last_digits=8)
    (tmp_path / f"{truncated}.nii.gz").write_text("x")

    kept, skipped = filter_samples_without_existing_output(samples, writer)

    assert [sample[0].PatientID for _, sample in kept] == ["Patient_B"]
    assert skipped == ["0000"]
