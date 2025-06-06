import pytest
from pathlib import Path
from click.testing import CliRunner
import os
from imgtools.cli.interlacer import interlacer as interlacer_cli
import shutil


@pytest.fixture(scope="function")
def runner() -> CliRunner:
    return CliRunner()

@pytest.fixture(scope="function")
def collection(request):
    data_dir = Path("data")
    
    value = request.param
    if not (data_dir / value).exists():
        yield value
    else:
        shutil.copytree(data_dir / value, data_dir / f"{value}-interlacer-test-temp", dirs_exist_ok=True)
        yield f"{value}-interlacer-test-temp"
        shutil.rmtree(data_dir / f"{value}-interlacer-test-temp")
        if (data_dir / ".imgtools" / f"{value}-interlacer-test-temp").exists():
            shutil.rmtree(data_dir / ".imgtools" / f"{value}-interlacer-test-temp")


@pytest.mark.parametrize("collection", [
    "CPTAC-UCEC",
    "NSCLC_Radiogenomics",
    "LIDC-IDRI",
    "Head-Neck-PET-CT",
    "HNSCC",
    "Pancreatic-CT-CBCT-SEG",
], indirect=True)
def test_interlacer_collections(
    runner: CliRunner,
    medimage_by_collection,
    collection: str,
    dataset_type: str,
):
    """Test `imgtools interlacer` on each collection from public or private sets."""
 

    input_dir = Path("data") / collection

    if not Path(input_dir).exists():
        pytest.skip(f"Collection {collection} not found {dataset_type=}")

    print(f"Testing {collection} in {input_dir}")
    out_dir = input_dir.parent / ".imgtools" / collection

    result = runner.invoke(interlacer_cli, [
        str(input_dir),
        "--n-jobs", "1",
        "--force"
    ])

    assert result.exit_code == 0, f"{collection} failed: {result.exception}\n {result.exc_info}"

    result = runner.invoke(interlacer_cli, [
        str(out_dir / "index.csv"),
    ])

    assert result.exit_code == 0, f"{collection} failed: {result.exception}\n {result.exc_info}"

    os.remove(out_dir / "index.csv")

    result = runner.invoke(interlacer_cli, [
        str(input_dir),
    ])

    assert result.exit_code == 0, f"{collection} failed: {result.exception}\n {result.exc_info}"
