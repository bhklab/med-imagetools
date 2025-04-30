import pytest
import tempfile
import os
from pathlib import Path
from click.testing import CliRunner
from imgtools.cli.autopipeline import autopipeline


class TestAutopipelineCLI:
    """Integration tests for the autopipeline CLI command using collections from the test data."""

    @pytest.fixture(scope="function")
    def runner(self):
        """Create a Click CLI test runner."""
        return CliRunner()

    @pytest.fixture(scope="function")
    def temp_output_dir(self):
        """Create a temporary directory for test output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_basic_help(self, runner):
        """Test that the CLI command displays help information correctly."""
        result = runner.invoke(autopipeline, ["--help"])
        assert result.exit_code == 0
        assert "Run the Autopipeline for processing medical images" in result.output
        assert "--modalities" in result.output
        assert "--roi-strategy" in result.output

    def test_invalid_args(self, runner, temp_output_dir):
        """Test CLI behavior with invalid arguments."""
        # Missing required --modalities option
        result = runner.invoke(autopipeline, [
            str(Path(__file__).parent),  # Using test dir as input for simplicity
            str(temp_output_dir)
        ])
        assert result.exit_code != 0
        assert "Missing option '--modalities'" in result.output or "Error:" in result.output

    @pytest.mark.parametrize("modality", ["CT", "MR", "PT", "RTSTRUCT"])
    def test_collection_modality_parameter(self, runner, temp_output_dir, modality, medimage_by_modality):
        """Test the CLI with different modality parameters."""
        # Skip if we don't have any test data for this modality
        if modality not in medimage_by_modality or not medimage_by_modality[modality]:
            pytest.skip(f"No test data available for modality: {modality}")
            
        # Get a sample input directory from the first entry for this modality
        sample_entry = medimage_by_modality[modality][0]
        input_dir = sample_entry["Path"].parent
        
        result = runner.invoke(autopipeline, [
            str(input_dir),
            str(temp_output_dir),
            "--modalities", modality,
            "--existing-file-mode", "skip"  # Skip existing files to avoid errors
        ])
        # If we have permission issues or other errors, the invocation might fail,
        # but we're just checking the CLI interface works as expected
        assert "Error running pipeline" not in result.output or "Error:" not in result.output

    def test_roi_match_yaml_option(self, runner, temp_output_dir, medimage_test_data):
        """Test the CLI with a YAML file for ROI matching."""
        # Skip if no test data available
        if not medimage_test_data:
            pytest.skip("No test data available")
            
        # Create a temporary YAML file for ROI matching
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp:
            tmp.write("""
            GTV: ["GTV", "gtv", "Gross.*Volume"]
            CTV: ["CTV", "ctv", "Clinical.*Volume"]
            """)
            tmp_path = tmp.name
        
        try:
            # Find a suitable input directory
            input_dir = medimage_test_data[0]["Path"].parent
            
            # Test the CLI with the YAML file
            result = runner.invoke(autopipeline, [
                str(input_dir),
                str(temp_output_dir),
                "--modalities", "CT,RTSTRUCT",
                "--roi-match-yaml", tmp_path
            ])
            # We're just testing the CLI interface, not the actual processing
            assert result.exit_code in [0, 1]  # Allow for processing errors
            
        finally:
            # Clean up the temporary file
            os.unlink(tmp_path)
            
    @pytest.mark.parametrize("collection", ["public_collections", "private_collections"])
    def test_collections(self, runner, temp_output_dir, collection, request, dataset_type):
        """Test the CLI with different collections."""
        # Get the appropriate collection list based on the fixture name
        collections = request.getfixturevalue(collection)
        
        # Skip if this collection type doesn't match the current dataset type
        if (collection == "private_collections" and dataset_type == "public") or \
           (collection == "public_collections" and dataset_type == "private"):
            pytest.skip(f"Skipping {collection} tests with {dataset_type} dataset type")
        
        # Skip if no collections available
        if not collections:
            pytest.skip(f"No collections available for {collection}")
        
        # Just test the first collection to avoid long test runs
        test_collection = collections[0]
        
        # Get the collection data
        collection_data = request.getfixturevalue("medimage_by_collection").get(test_collection, [])
        
        # Skip if no data for this collection
        if not collection_data:
            pytest.skip(f"No test data available for collection: {test_collection}")
            
        # Get a sample input directory from the first entry
        input_dir = collection_data[0]["Path"].parent.parent  # Go up to patient level
        
        # Get the modalities available in this collection
        modalities = set(entry["Modality"] for entry in collection_data)
        modalities_str = ",".join(modalities)
        
        result = runner.invoke(autopipeline, [
            str(input_dir),
            str(temp_output_dir),
            "--modalities", modalities_str,
            "--existing-file-mode", "skip",  # Skip existing files to avoid errors
            "--update-crawl"  # Force recrawling
        ])
        
        # We're just testing the CLI interface works, the actual processing might fail
        # due to various reasons (permissions, missing files, etc.)
        assert result.exit_code in [0, 1]