import pytest
from pathlib import Path
from click.testing import CliRunner
import os
from imgtools.cli.interlacer import interlacer as interlacer_cli


@pytest.fixture(scope="function")
def runner() -> CliRunner:
    return CliRunner()

# these are just randomly selected collections!
INDEXABLE_COLLECTIONS = [
    "CPTAC-UCEC",
    "NSCLC_Radiogenomics",
    "LIDC-IDRI",
    "Head-Neck-PET-CT",
    "HNSCC",
    "Pancreatic-CT-CBCT-SEG",
]

@pytest.mark.parametrize("collection", INDEXABLE_COLLECTIONS)
def test_interlacer_collections(
    runner: CliRunner,
    collection: str,
    medimage_by_collection,
    dataset_type: str,
):
    """Test `imgtools interlacer` on each collection from public or private sets."""


    if collection not in medimage_by_collection:
        pytest.skip(f"Collection {collection} not found in medimage_by_collection {dataset_type=}")

    input_dir = Path("data") / collection
    print(f"Testing {collection} in {input_dir}")
    out_dir = input_dir.parent / ".imgtools" / collection

    result = runner.invoke(interlacer_cli, [
        str(input_dir),
        "--n-jobs", "1",
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
