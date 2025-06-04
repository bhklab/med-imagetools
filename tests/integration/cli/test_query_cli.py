import pytest
from pathlib import Path
from click.testing import CliRunner
import os
from imgtools.cli.query import query as query_cli
import shutil


@pytest.fixture(scope="function")
def runner() -> CliRunner:
    return CliRunner()

@pytest.fixture(scope="function")
def collection(request):
    data_dir = Path("data")
    
    value = request.param
    if not (data_dir / value).exists():
        pytest.skip(f"Collection {value} not found in test data")
    else:
        shutil.copytree(data_dir / value, data_dir / f"{value}-query-test-temp", dirs_exist_ok=True)
        yield f"{value}-query-test-temp"
        shutil.rmtree(data_dir / f"{value}-query-test-temp")

@pytest.mark.parametrize("collection", [
    "CPTAC-UCEC",
    "NSCLC_Radiogenomics",
    "LIDC-IDRI",
    "Head-Neck-PET-CT",
    "HNSCC",
    "Pancreatic-CT-CBCT-SEG",
], indirect=True)
def test_query_collections(
    runner: CliRunner,
    medimage_by_collection,
    collection: str,
    dataset_type: str,
):
    """Test `imgtools query` on each collection from public or private sets."""
 

    input_dir = Path("data") / collection

    print(f"Testing {collection} in {input_dir}")
    out_dir = input_dir.parent / ".imgtools" / collection

    result = runner.invoke(query_cli, [
        str(input_dir),
        "CT,RTDOSE",
        "--n-jobs", "1",
    ])

    assert result.exit_code == 0, f"{collection} failed: {result.exception}\n {result.exc_info}"

    result = runner.invoke(query_cli, [
        str(out_dir / "index.csv"),
        "CT,RTDOSE",
    ])

    assert result.exit_code == 0, f"{collection} failed: {result.exception}\n {result.exc_info}"

    # replace os.remove with pathlib and guard against missing file
    index_file = out_dir / "index.csv"
    if index_file.exists():
        index_file.unlink()

    result = runner.invoke(query_cli, [
        str(input_dir),
        "CT,RTDOSE",
    ])

    assert result.exit_code == 0, f"{collection} failed: {result.exception}\n {result.exc_info}"
