"""Tests for ignoring samples with existing writer output."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from imgtools.autopipeline_utils import (
    filter_samples_without_existing_output,
    resolve_sample_output_path,
    sample_output_exists,
)
from imgtools.io.writers import ExistingFileMode, NIFTIWriter
from imgtools.io.sample_output import DEFAULT_FILENAME_FORMAT


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


def _writer(tmp_path: Path, filename_format: str = DEFAULT_FILENAME_FORMAT) -> NIFTIWriter:
    return NIFTIWriter(
        root_directory=tmp_path,
        filename_format=filename_format,
        existing_file_mode=ExistingFileMode.OVERWRITE,
        create_dirs=True,
    )


def test_resolve_sample_output_path_uses_writer_format(tmp_path: Path) -> None:
    writer = _writer(tmp_path)
    sample = _sample("Patient_A", series_uid="1.2.3.45678901")

    resolved = resolve_sample_output_path(writer, sample, "0000")

    assert resolved.parent.parent == tmp_path / "0000__Patient_A"
    assert "CT_" in resolved.parent.name


def test_sample_output_exists_for_nested_format(tmp_path: Path) -> None:
    writer = _writer(tmp_path)
    sample = _sample("Patient_A")

    assert not sample_output_exists(writer, sample, "0000")

    sample_dir = tmp_path / "0000__Patient_A"
    sample_dir.mkdir()
    (sample_dir / "marker.txt").write_text("done")

    assert sample_output_exists(writer, sample, "0000")


def test_sample_output_exists_for_patient_format(tmp_path: Path) -> None:
    writer = _writer(tmp_path, "{PatientID}/{Modality}/{ImageID}.nii.gz")
    sample = _sample("Patient_B")

    assert not sample_output_exists(writer, sample, "0001")

    patient_dir = tmp_path / "Patient_B"
    patient_dir.mkdir()
    (patient_dir / "CT").mkdir()
    (patient_dir / "CT" / "CT.nii.gz").write_text("x")

    assert sample_output_exists(writer, sample, "0001")


def test_sample_output_exists_for_flat_format(tmp_path: Path) -> None:
    writer = _writer(tmp_path, "{PatientID}_{Modality}.nii.gz")
    sample = _sample("Patient_C")

    assert not sample_output_exists(writer, sample, "0000")
    (tmp_path / "Patient_C_CT.nii.gz").write_text("x")
    assert sample_output_exists(writer, sample, "0000")


def test_filter_preserves_sample_numbers(tmp_path: Path) -> None:
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
    assert skipped == ["0001:Patient_B"]


def test_filter_keeps_all_when_no_existing_output(tmp_path: Path) -> None:
    writer = _writer(tmp_path)
    samples = [_sample("Patient_A"), _sample("Patient_B")]

    kept, skipped = filter_samples_without_existing_output(samples, writer)

    assert len(kept) == 2
    assert skipped == []
