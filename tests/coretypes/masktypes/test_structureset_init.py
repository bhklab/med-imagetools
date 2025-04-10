from imgtools.coretypes.masktypes.structureset import RTStructureSet
import pytest
from rich import print
# import the `MedImageDataEntry` class from the conftest.py file
from tests.conftest import MedImageDataEntry

@pytest.fixture(scope="function")
def all_rtstructs(medimage_by_modality: dict[str, list[MedImageDataEntry]]) -> list[MedImageDataEntry]:
    """Fixture to provide all RTSTRUCT entries."""
    return medimage_by_modality["RTSTRUCT"]

def test_rtstruct_init(all_rtstructs: list[MedImageDataEntry]):
    """Test the initialization of RTStructureSet."""
    for i, entry in enumerate(all_rtstructs):
        # Create an instance of RTStructureSet
        rtstruct = RTStructureSet.from_dicom(entry['Path'], suppress_warnings=True)
        
        # Check if the instance is created successfully
        assert isinstance(rtstruct, RTStructureSet), f"RTStructureSet {i} initialization failed"

        assert len(rtstruct) > 0, f"RTStructureSet {i} should contain structures"
