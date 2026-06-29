import pytest
from pathlib import Path
from click.testing import CliRunner
from imgtools.cli.dicomshow import dicomshow as dicomshow_cli
from typing import Any
from sys import platform
import glob

@pytest.fixture(scope="function")
def runner() -> CliRunner:
    return CliRunner()

@pytest.fixture(scope="function")
def collection(request):
    data_dir = Path("data")
    
    value = request.param
    if not (data_dir / value).exists():
        pytest.skip(f"{value} dataset unavailable.")
    else:
        dicoms = {}
        for modality in ["CT", "SEG", "RTSTRUCT", "MR", "REG", "RTDOSE", "PT", "RTPLAN", "SR"]:
            dicom_by_modality = sorted(glob.glob(str(data_dir/value)+f"/**/{modality}*/*.dcm", recursive=True))
            if dicom_by_modality:
                dicoms[modality] = dicom_by_modality[0]
        return dicoms, value



@pytest.mark.parametrize("collection", [
    "CPTAC-UCEC",
    "NSCLC_Radiogenomics",
    "Head-Neck-PET-CT",
    "HNSCC",
    "Pancreatic-CT-CBCT-SEG",
], indirect=True)
def test_dicomshow_collections(
    runner: CliRunner,
    collection: tuple[dict[str, str], str],
    snapshot: Any,
):
    """Test `imgtools dicomshow` on each collection from public or private sets."""
    collection_dicoms, collection_name = collection
    snapshot.snapshot_dir = f'tests/snapshots/dicomshow/{collection_name}_snapshots'
    for modality in collection_dicoms:
        result = runner.invoke(dicomshow_cli, [
            str(collection_dicoms[modality]), 
            "--no-progress"
        ])
        if platform == "darwin":
            # snapshots were taken on macos, so we only use them if testing the macos platform. 
            snapshot.assert_match(
                result.stdout_bytes,
                f'{collection_name}_{modality}_default'
            )
        assert result.exit_code == 0, (
            f"{collection_name} failed on {modality} "
            f"{collection_dicoms[modality]} (default parameters): "
            f"{result.exception}\n{result.exc_info}"
        )

        result = runner.invoke(dicomshow_cli, [
            str(collection_dicoms[modality]),
            "--no-progress",
            "-p"
        ])
        if platform == "darwin":
            # snapshots were taken on macos, so we only use them if testing the macos platform. 
            snapshot.assert_match(
                result.stdout_bytes,
                f'{collection_name}_{modality}_pydicom'
            )
        assert result.exit_code == 0, (
            f"{collection_name} failed on {modality} (--pydicom enabled): "
            f"{result.exception}\n{result.exc_info}"
        )
    