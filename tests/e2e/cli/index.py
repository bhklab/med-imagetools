import pytest
from pathlib import Path
from click.testing import CliRunner

from imgtools.cli.index import index as index_cli


@pytest.fixture(scope="function")
def runner() -> CliRunner:
    return CliRunner()


@pytest.mark.parametrize("collection", ["public_collections", "private_collections"])
def test_index_collections(
    runner: CliRunner,
    tmp_path: Path,
    collection: str,
    request: pytest.FixtureRequest,
    medimage_by_collection,
    dataset_type: str,
):
    """Test `imgtools index` on each collection from public or private sets."""

    # Skip irrelevant collection type
    if (collection == "private_collections" and dataset_type == "public") or \
       (collection == "public_collections" and dataset_type == "private"):
        pytest.skip(f"Skipping {collection} for dataset type: {dataset_type}")

    collections = request.getfixturevalue(collection)
    if not collections:
        pytest.skip(f"No collections in {collection}")

    for collection_name in collections:
        data = medimage_by_collection.get(collection_name, [])
        if not data:
            continue

        input_dir = Path("data") / collection_name
        print(f"Testing {collection_name} in {input_dir}")
        out_dir = input_dir.parent / ".imgtools" / collection_name

        result = runner.invoke(index_cli, [
            "--n-jobs", "1",
            "--dicom-dir", str(input_dir),
            "--force"
        ])

        assert result.exit_code == 0, f"{collection_name} failed: {result.output}"
        assert out_dir.exists()
        
        files = [
            out_dir / "index.csv"
        ]
    
        for file in files:
            assert file.exists(), f"File {file} does not exist"

        # Only index one per collection type per test to keep test time short
        # return
