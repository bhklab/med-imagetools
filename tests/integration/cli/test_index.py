import sys
import pytest
from pathlib import Path
from click.testing import CliRunner

from imgtools.cli.index import index as index_cli
from imgtools.dicom.crawl.crawler import CrawlerOutputDirError


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


class TestIndexOutputDirectory:
    """Test various output directory scenarios for the indexing command.
    
    Yeah, so we just added this validate_output_dir function to the crawler.py file
    and now we need to make sure it actually works the way we expect. These tests
    check different output directory situations:
    
    - read-only directories
    - non-existent directories
    - files instead of directories
    - etc.
    
    We want to make sure we get the right error messages so users aren't confused.
    """
    
    @pytest.fixture
    def temp_output_dir(self, tmp_path):
        """Create a temporary directory for test output."""
        output_dir = tmp_path / "output_dir"
        output_dir.mkdir()
        return output_dir
    
    @pytest.fixture
    def sample_dicom_dir(self, medimage_by_collection):
        """Get a path to a sample DICOM directory for testing."""
        # Just grab the first available collection for testing
        for collection in INDEXABLE_COLLECTIONS:
            if collection in medimage_by_collection:
                return medimage_by_collection[collection][0]["Path"]
        # Fallback - use any available collection
        for collection, entries in medimage_by_collection.items():
            if entries:
                return entries[0]["Path"]
        pytest.skip("No test data collections available")
    
    def test_nonexistent_output_dir_gets_created(self, runner, sample_dicom_dir, tmp_path):
        """Test that non-existent output directories get created automatically."""
        output_dir = tmp_path / "nonexistent_dir"

        
        
        # Make sure it doesn't exist yet
        assert not output_dir.exists()
        
        result = runner.invoke(index_cli, [
            "--dicom-dir", str(sample_dicom_dir),
            "--output-dir", str(output_dir),
            "--n-jobs", "1",
        ])
        
        # Should succeed and create the directory
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert output_dir.exists()
        assert output_dir.is_dir()
    
    def test_file_as_output_dir_fails(self, runner, sample_dicom_dir, tmp_path):
        """Test that using a file as output directory fails with appropriate error."""
        # Create a file instead of a directory
        file_path = tmp_path / "output_file.txt"
        file_path.write_text("This is a file, not a directory")
        
        result = runner.invoke(index_cli, [
            "--dicom-dir", str(sample_dicom_dir),
            "--output-dir", str(file_path),
            "--n-jobs", "1",
        ])
        
        # Should fail with appropriate error message
        assert result.exit_code != 0
        assert "is not a directory" in result.output
    
    @pytest.mark.skipif(
        sys.platform == 'win32', 
        reason="Permission tests behave differently on Windows"
    )
    def test_readonly_output_dir_fails(self, runner, sample_dicom_dir, temp_output_dir):
        """Test that using a read-only directory fails with permissions error."""
        try:
            # Make the directory read-only
            temp_output_dir.chmod(0o500)  # read & execute only, no write
            
            result = runner.invoke(index_cli, [
                "--dicom-dir", str(sample_dicom_dir),
                "--output-dir", str(temp_output_dir),
                "--n-jobs", "1",
            ])
            
            # Should fail with permissions error
            assert result.exit_code != 0
            assert "not writable" in result.output
            
        finally:
            # Make sure to restore permissions so test cleanup doesn't fail
            temp_output_dir.chmod(0o700)
    
    @pytest.mark.skipif(
        "sys.platform == 'win32'", 
        reason="Permission tests behave differently on Windows"
    )
    def test_parent_not_writable_fails(self, runner, sample_dicom_dir, tmp_path):
        """Test handling of case where parent directory exists but isn't writable."""
        parent_dir = tmp_path / "parent_dir"
        parent_dir.mkdir()
        nested_dir = parent_dir / "nested_dir"
        
        try:
            # Make the parent directory read-only
            parent_dir.chmod(0o500)  # read & execute only, no write
            
            result = runner.invoke(index_cli, [
                "--dicom-dir", str(sample_dicom_dir),
                "--output-dir", str(nested_dir),  # This doesn't exist yet
                "--n-jobs", "1",
            ])
            
            # Should fail with appropriate error
            assert result.exit_code != 0
            assert "create output directory" in result.output.lower() or "permission" in result.output.lower()
            
        finally:
            # Make sure to restore permissions so test cleanup doesn't fail
            parent_dir.chmod(0o700)


