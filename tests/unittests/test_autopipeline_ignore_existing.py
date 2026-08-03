"""Tests for ignoring patients with existing output folders."""

from __future__ import annotations

from types import SimpleNamespace

from imgtools.autopipeline_utils import (
    extract_patient_id_from_folder_name,
    filter_samples_without_existing_folders,
    find_existing_patient_ids,
)


def _sample(patient_id: str):
    return [SimpleNamespace(PatientID=patient_id)]


def test_extract_patient_id_from_sample_number_folder() -> None:
    assert extract_patient_id_from_folder_name("0003__Patient_A") == "Patient_A"


def test_extract_patient_id_from_bare_patient_folder() -> None:
    assert extract_patient_id_from_folder_name("Patient_A") == "Patient_A"


def test_find_existing_patient_ids(tmp_path) -> None:
    (tmp_path / "0000__Patient_A").mkdir()
    (tmp_path / "Patient_B").mkdir()
    (tmp_path / ".hidden").mkdir()
    (tmp_path / "not_a_dir.txt").write_text("x")

    assert find_existing_patient_ids(tmp_path) == {"Patient_A", "Patient_B"}


def test_filter_samples_without_existing_folders(tmp_path) -> None:
    (tmp_path / "0001__Patient_A").mkdir()

    samples = [_sample("Patient_A"), _sample("Patient_B")]
    kept, skipped = filter_samples_without_existing_folders(samples, tmp_path)

    assert [s[0].PatientID for s in kept] == ["Patient_B"]
    assert skipped == ["Patient_A"]


def test_filter_sanitizes_patient_ids(tmp_path) -> None:
    (tmp_path / "0000__Patient_With_Spaces").mkdir()

    samples = [_sample("Patient With Spaces"), _sample("Other")]
    kept, skipped = filter_samples_without_existing_folders(samples, tmp_path)

    assert [s[0].PatientID for s in kept] == ["Other"]
    assert skipped == ["Patient With Spaces"]


def test_filter_keeps_all_when_no_existing_folders(tmp_path) -> None:
    samples = [_sample("Patient_A"), _sample("Patient_B")]
    kept, skipped = filter_samples_without_existing_folders(samples, tmp_path)

    assert len(kept) == 2
    assert skipped == []
