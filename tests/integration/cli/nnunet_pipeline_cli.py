import pytest
import tempfile
import os
import yaml
import subprocess
from sys import platform
from pathlib import Path
from click.testing import CliRunner
from imgtools.cli.nnunet_pipeline import nnunet_pipeline


class TestnnUNetCLI:
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
        result = runner.invoke(nnunet_pipeline, ["--help"])
        assert result.exit_code == 0
        assert "Process medical images in nnUNet format." in result.output
        assert "--modalities" in result.output
        assert "--roi-match-yaml" in result.output

    def test_invalid_args(self, runner, temp_output_dir):
        """Test CLI behavior with invalid arguments."""
        # Missing required --modalities option
        result = runner.invoke(nnunet_pipeline, [
            str(Path(__file__).parent),  # Using test dir as input for simplicity
            str(temp_output_dir)
        ])
        assert result.exit_code != 0
        assert "Missing option '--modalities'" in result.output or "Error:" in result.output

        result = runner.invoke(nnunet_pipeline, [
            str(Path(__file__).parent),  # Using test dir as input for simplicity
            str(temp_output_dir),
            "--modalities", "CT,RTSTRUCT"
        ])
        assert result.exit_code != 0
        assert "Missing option '--roi-match-yaml' / '-ryaml'" in result.output or "Error:" in result.output

    @pytest.mark.skipif(platform == "darwin", reason="Test skipped on macOS, due to nnUNet py313 incompatibility")
    @pytest.mark.parametrize("mask_saving_strategy", ["sparse_mask", "region_mask"])
    def test_RADCURE(self, runner, temp_output_dir, DATA_DIR, mask_saving_strategy):
        """Test the CLI with different collections."""
            
        input_dir = DATA_DIR / "RADCURE"
        if not input_dir.exists():
            pytest.skip("RADCURE test data not available")

        modalities_str = "CT,RTSTRUCT"

        roi_dict = {
            "BRAINSTEM": "Brainstem",
            "SPINALCORD": "SpinalCord",
            "LARYNX": "Larynx",
        }
        roi_yaml_path = input_dir / "roi_match.yaml"
        with (roi_yaml_path).open("w") as f:
            yaml.dump(roi_dict, f)

        result = runner.invoke(nnunet_pipeline, [
            str(input_dir),
            str(temp_output_dir),
            "--modalities", modalities_str,
            "--roi-match-yaml", str(roi_yaml_path),
            "--existing-file-mode", "skip",  # Skip existing files to avoid errors
            "--mask-saving-strategy", mask_saving_strategy,
        ])
        
        assert result.exit_code == 0, "imgtools nnunet_pipeline failed"
        
        env = os.environ.copy()
        env["nnUNet_raw"] = (temp_output_dir / "nnUNet_raw").as_posix()
        env["nnUNet_preprocessed"] = (temp_output_dir / "nnUNet_preprocessed").as_posix()
        env["nnUNet_results"] = (temp_output_dir / "nnUNet_results").as_posix()
        nnunet_result = subprocess.run([
            "nnUNetv2_extract_fingerprint",
            "-d", "1",
            "--verify_dataset_integrity",
            ],
            env=env,
            stdout=subprocess.PIPE
        )

        assert nnunet_result.returncode == 0, "nnUNetv2_extract_fingerprint failed"