import pytest
from pathlib import Path
from click.testing import CliRunner
import os
from imgtools.cli.dicomsort import dicomsort as dicomsort_cli
from imgtools.cli.testdatasets import testdata as download_github_cli
from tests.conftest import MedImageDataEntry


@pytest.fixture(scope="function")
def runner() -> CliRunner:
    return CliRunner()

@pytest.mark.skipif(
    os.getenv("TEST_DATASET_TYPE", "public").lower() == 'private',
    reason="Test uses collections in public data"
)
def test_dicomsort(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
#     ❯ imgtools dicomsort -h
# Usage: imgtools dicomsort [OPTIONS] SOURCE_DIRECTORY TARGET_DIRECTORY

#   Sorts DICOM files into directories based on their tags.

# Options:
#   -a, --action [move|copy|symlink|hardlink]
#                                   Action to perform on the files.  [required]
#   -n, --dry-run                   Do not move or copy files, just print what
#                                   would be done. Always recommended to use
#                                   this first to confirm the operation!
#   -j, --num-workers INTEGER       Number of worker processes to use for
#                                   sorting.  [default: 1]
#   -t, --truncate-uids INTEGER     Truncate the UIDs in the DICOM files to the
#                                   specified length. Set to 0 to disable
#                                   truncation.
#   -h, --help                      Show this message and exit.
    input_dir = Path("data") / "NSCLC-Radiomics"
    # Now inspect the output structure
    root_output = tmp_path / "dicomsort_output"
    output_dir = str(root_output.absolute()) + "/%PatientID/%Modality_%SeriesInstanceUID/"
    download_result = runner.invoke(
        download_github_cli,
        [
            "-d", "data",
            "-a", "NSCLC-Radiomics",
        ],
    )
    assert download_result.exit_code == 0, "Failed to download test data"

    result  = runner.invoke(
        dicomsort_cli,
        [
            "--action",
            "copy",
            "--num-workers",
            "1",
            "--truncate-uids",
            "10",
            str(input_dir),
            str(output_dir),
        ],
    )

    assert result.exit_code == 0

    expected_structure = {
        "LUNG1-001": {"CT_2563382046", "RTSTRUCT_0535578236", "SEG_260509.554"},
        "LUNG1-002": {"CT_1323261228", "RTSTRUCT_7543245931", "SEG_260515.421"},
    }

    assert root_output.exists(), "Output directory not created"

    print(f"{list(root_output.iterdir())=}")
    for patient_id, expected_subdirs in expected_structure.items():
        patient_dir = root_output / patient_id
        assert patient_dir.exists() and patient_dir.is_dir(), f"{patient_id} missing"

        actual_subdirs = {p.name for p in patient_dir.iterdir() if p.is_dir()}
        assert actual_subdirs == expected_subdirs, \
            f"Mismatch in {patient_id}: expected {expected_subdirs}, got {actual_subdirs}"


    # Test --dry-run
    #     ‼ Dry run mode enabled. No files will be moved or copied. ‼ 

    # Common Prefix: 📁/home/jermiah/bhklab/radiomics/Projects/med-imagetools/temp_outputs


    # Preview of the parsed pattern and sample paths as directories:

    # 📁 /home/jermiah/bhklab/radiomics/Projects/med-imagetools/temp_outputs/
    # ┣━━ {PatientID}_{SeriesInstanceUID} (6 unique)
    # ┣━━ LUNG1-001_78236
    # ┣━━ ...
    # ┗━━ LUNG1-002_61228
    #     ┣━━ 00000002.dcm
    #     ┣━━ 00000003.dcm
    #     ┣━━ ...
    #     ┗━━ 00000111.dcm

    dry_result = runner.invoke(
        dicomsort_cli,
        [
            "--action",
            "copy",
            "--num-workers",
            "1",
            "--truncate-uids",
            "10",
            "--dry-run",
            str(input_dir),
            str(output_dir + "dry"),
        ],
    )
    assert dry_result.exit_code == 0
    assert "‼ Dry run mode enabled. No files will be moved or copied. ‼" in dry_result.output


    # test invalid key
    invalid = runner.invoke(
        dicomsort_cli,
        [
            "--action",
            "copy",
            "--num-workers",
            "1",
            "--truncate-uids",
            "10",
            "--dry-run",
            str(input_dir),
            str(output_dir + "%dry/"),
        ],
    )
    assert invalid.exit_code > 0, "Command should fail with an error code for invalid key"