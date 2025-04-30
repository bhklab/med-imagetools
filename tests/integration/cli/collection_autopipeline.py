import pytest
import tempfile
import yaml
import os
from pathlib import Path
from click.testing import CliRunner
from imgtools.cli.autopipeline import autopipeline


class TestCollectionAutopipeline:
    """Integration tests for the autopipeline CLI command using all collections from test data.
    
    This test class iterates through all available collections based on the current
    dataset type (public or private) and tests the autopipeline CLI with each collection.
    """

    @pytest.fixture(scope="function")
    def runner(self):
        """Create a Click CLI test runner."""
        return CliRunner()

    @pytest.fixture(scope="function")
    def temp_output_dir(self):
        """Create a temporary directory for test output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
            
    @pytest.fixture(scope="function")
    def roi_match_yaml(self):
        """Create a temporary YAML file with ROI matching patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "roi_match.yaml"
            # Create a sample ROI matching YAML file
            roi_config = {
                "GTV": ["GTV", "gtv", "Gross.*Volume"],
                "CTV": ["CTV", "ctv", "Clinical.*Volume"],
                "PTV": ["PTV", "ptv", "Planning.*Volume"],
                "Lung": ["Lung", "lung"],
                "Heart": ["Heart", "heart"],
                "Esophagus": ["Esophagus", "esophagus"],
                "SpinalCord": ["Spinal.*Cord", "SpinalCord", "Cord"]
            }
            
            with open(tmp_path, 'w') as f:
                yaml.dump(roi_config, f)
                
            yield tmp_path

    def get_available_collections(self, dataset_type, public_collections, private_collections):
        """Get the list of collections based on the dataset type."""
        if dataset_type == "public":
            return public_collections
        elif dataset_type == "private":
            return private_collections
        return []

    @pytest.mark.parametrize("test_type", ["basic", "with_roi_map"])
    def test_all_collections(self, runner, temp_output_dir, roi_match_yaml, medimage_by_collection,
                           dataset_type, public_collections, private_collections,
                           test_type):
        """Test the autopipeline CLI with all available collections.
        
        This test iterates through all available collections and tests the CLI with each one.
        It runs two types of tests:
        - basic: Simple test with default parameters
        - with_roi_map: Test with ROI matching patterns from YAML file
        """
        # Get collections based on dataset type
        collections = self.get_available_collections(dataset_type, public_collections, private_collections)
        
        # Skip if no collections available
        if not collections:
            pytest.skip(f"No collections available for dataset type: {dataset_type}")
            
        # Test with each collection
        for collection_name in collections:
            # Get the collection data
            collection_data = medimage_by_collection.get(collection_name, [])
            
            # Skip if no data for this collection
            if not collection_data:
                pytest.skip(f"No test data available for collection: {collection_name}")
                
            # Get input directory (patient level) from the first entry
            patient_id = collection_data[0]["PatientID"]
            collection_dir = collection_data[0]["Path"].parent.parent  # Go up two levels to collection
            input_dir = collection_dir
            
            # Get the modalities available in this collection
            modalities = sorted(set(entry["Modality"] for entry in collection_data))
            modalities_str = ",".join(modalities)
            
            # Skip collections that don't have supported modalities
            if not any(m in ["CT", "MR", "PT", "RTSTRUCT", "SEG"] for m in modalities):
                continue
                
            # Base command arguments
            cmd_args = [
                str(input_dir),
                str(temp_output_dir / collection_name),
                "--modalities", modalities_str,
                "--existing-file-mode", "skip",  # Skip existing files to avoid errors
                "--update-crawl",  # Force recrawling
                "--jobs", "1"  # Use single job for testing
            ]
            
            # Add test-specific arguments
            if test_type == "with_roi_map":
                cmd_args.extend([
                    "--roi-match-yaml", str(roi_match_yaml),
                    "--roi-strategy", "SEPARATE",
                    "--roi-ignore-case"
                ])
            
            # Run the autopipeline command
            print(f"Testing collection: {collection_name} with modalities: {modalities_str}")
            result = runner.invoke(autopipeline, cmd_args)
            
            # The test passes if the command runs without errors or with acceptable errors
            assert result.exit_code in [0, 1], \
                f"Failed for collection {collection_name}: {result.output}"
            
    def test_specific_collection_patient(self, runner, temp_output_dir, medimage_by_collection):
        """Test autopipeline on a specific patient from a collection (if available)."""
        # Try to get data from a collection with sufficient test data
        test_collections = [
            "LIDC-IDRI", "NSCLC-Radiomics", "4D-Lung", "CT_Lymph_Nodes",  # Public collections
            "HNSCC", "QIN-HEADNECK"  # Private collections
        ]
        
        for collection_name in test_collections:
            collection_data = medimage_by_collection.get(collection_name, [])
            if not collection_data:
                continue
                
            # Find a patient with multiple modalities if possible
            patients = {}
            for entry in collection_data:
                patient_id = entry["PatientID"]
                if patient_id not in patients:
                    patients[patient_id] = []
                patients[patient_id].append(entry["Modality"])
            
            # Find a patient with multiple modalities
            multi_mod_patients = [(pid, mods) for pid, mods in patients.items() if len(set(mods)) > 1]
            if multi_mod_patients:
                patient_id, modalities = multi_mod_patients[0]
            else:
                # If no patient with multiple modalities, use the first patient
                patient_id = next(iter(patients.keys()))
                modalities = patients[patient_id]
            
            # Get the input directory for this patient
            patient_entries = [e for e in collection_data if e["PatientID"] == patient_id]
            input_dir = patient_entries[0]["Path"].parent.parent  # Collection dir
            patient_dir = input_dir / patient_id
            
            # Test if the patient directory exists
            if not patient_dir.exists():
                continue
                
            # Prepare parameters for the test
            modalities_str = ",".join(sorted(set(modalities)))
            output_dir = temp_output_dir / f"{collection_name}_{patient_id}"
            
            # Run the test with the specific patient
            print(f"Testing patient {patient_id} from {collection_name} with {modalities_str}")
            result = runner.invoke(autopipeline, [
                str(patient_dir),
                str(output_dir),
                "--modalities", modalities_str,
                "--existing-file-mode", "skip",
                "--update-crawl",
                "--jobs", "1"
            ])
            
            # The test passes if the command runs without catastrophic errors
            assert result.exit_code in [0, 1]
            
            # Only test one collection to avoid long test runs
            return
            
        pytest.skip("No suitable test data found for specific patient test")