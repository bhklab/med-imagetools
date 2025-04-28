import pytest
from pathlib import Path
from imgtools.dicom import tag_exists
from imgtools.dicom.dicom_metadata import get_extractor, supported_modalities, register_extractor, ExistingExtractorError
from imgtools.dicom.dicom_metadata.extractor_base import ModalityMetadataExtractor
import sys

def test_base_tags_exist() -> None:
  """Ensure all base tags defined in ModalityMetadataExtractor exist."""
  missing = [tag for tag in ModalityMetadataExtractor.base_tags if not tag_exists(tag)]
  assert not missing, f"Missing base DICOM tags: {missing}"

def test_registering_existing_extractor() -> None:
  """Ensure that registering an existing extractor raises an error."""
  extractor = get_extractor("CT")
  with pytest.raises(ExistingExtractorError):
    register_extractor(extractor)

@pytest.mark.parametrize("modality", supported_modalities())
# def test_modality_tags_exist(modality: str, medimage_test_data: list[dict[str, str | Path]]) -> None:
def test_modality_tags_exist(modality: str) -> None:
  """Ensure all modality-specific tags exist for a given extractor."""
  extractor = get_extractor(modality)
  missing = [tag for tag in extractor.modality_tags if not tag_exists(tag)]
  assert not missing, f"Missing tags for modality '{modality}': {missing}"

  # make sure metadata_keys works
  assert extractor.metadata_keys()

#   mandatory_tags = {"PatientID", "StudyInstanceUID", "SeriesInstanceUID"}
#   count = 0

  # THIS SHOUD BE MOVED TO INTEGRATION TESTS
#   # check if extractor works for test data
#   for x in filter(lambda d: d['Modality'] == modality, medimage_test_data):
#     # get the filrst file in the directory
#     all_files = list(Path(x['Path']).glob("**/*.dcm"))

#     data = extractor.extract(all_files[0])

#     for tag in mandatory_tags:
#       value = data.get(tag)
#       if isinstance(value, str):
#         assert (len(value)>3), f"Mandatory tag '{tag}' not found in {modality} metadata"
#       else:
#         assert value is not None, f"Mandatory tag '{tag}' not found in {modality} metadata"
#     count += 1

#   if modality != "MR": # private data has no MR...
#     assert count > 0, f"No test data found for modality '{modality}'"