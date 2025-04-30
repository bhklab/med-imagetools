import pytest
from pathlib import Path
from click.testing import CliRunner

from imgtools.cli.index import index as index_cli


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
def test_index_collections(
    runner: CliRunner,
    collection: str,
    medimage_by_collection,
    dataset_type: str,
):
    """Test `imgtools index` on each collection from public or private sets."""


    if collection not in medimage_by_collection:
        pytest.skip(f"Collection {collection} not found in medimage_by_collection {dataset_type=}")

    input_dir = Path("data") / collection
    print(f"Testing {collection} in {input_dir}")
    out_dir = input_dir.parent / ".imgtools" / collection

    result = runner.invoke(index_cli, [
        "--n-jobs", "1",
        "--dicom-dir", str(input_dir),
        "--force"
    ])

    assert result.exit_code == 0, f"{collection} failed: {result.output}"
    assert out_dir.exists()

    files = [
        out_dir / "index.csv"
    ]

    for file in files:
        assert file.exists(), f"File {file} does not exist"
