from pathlib import Path
import pytest
import pydicom
from imgtools.dicom.dicom_metadata import extract_dicom_tags, MODALITY_TAGS
from imgtools.dicom import tag_exists
@pytest.fixture
def sample_dicom_dataset():
    # Create a minimal DICOM dataset for testing
    ds = pydicom.Dataset()
    ds.Modality = 'CT'
    ds.BodyPartExamined = 'CHEST'
    ds.SliceThickness = '2.5'
    ds.Manufacturer = 'TEST_MANUFACTURER'
    ds.KVP = '120'
    ds.file_meta = pydicom.Dataset()
    ds.is_implicit_VR = True
    ds.is_little_endian = True
    return ds

def test_extract_dicom_tags_with_modality(sample_dicom_dataset):
    tags = extract_dicom_tags(sample_dicom_dataset, modality='CT')
    assert isinstance(tags, dict)
    assert tags['BodyPartExamined'] == 'CHEST'
    assert tags['SliceThickness'] == '2.5'
    assert tags['Manufacturer'] == 'TEST_MANUFACTURER'
    assert tags['KVP'] == '120'

def test_extract_dicom_tags_without_modality(sample_dicom_dataset):
    tags = extract_dicom_tags(sample_dicom_dataset)
    assert isinstance(tags, dict)
    assert tags['BodyPartExamined'] == 'CHEST'
    assert tags['Manufacturer'] == 'TEST_MANUFACTURER'

def test_extract_dicom_tags_missing_tag(sample_dicom_dataset):
    tags = extract_dicom_tags(sample_dicom_dataset)
    assert tags['DataCollectionDiameter'] == 'None'

def test_extract_dicom_tags_no_modality():
    ds = pydicom.Dataset()
    with pytest.raises(ValueError, match="Modality not found in DICOM dataset."):
        extract_dicom_tags(ds)

def test_modality_tags_structure():
    assert 'ALL' in MODALITY_TAGS
    assert 'CT' in MODALITY_TAGS
    assert 'MR' in MODALITY_TAGS
    assert 'PT' in MODALITY_TAGS
    
    # Check that ALL contains common tags
    assert 'BodyPartExamined' in MODALITY_TAGS['ALL']
    assert 'SliceThickness' in MODALITY_TAGS['ALL']
    
    # Check modality specific tags
    assert 'KVP' in MODALITY_TAGS['CT']
    assert 'MagneticFieldStrength' in MODALITY_TAGS['MR']
    assert 'RadionuclideTotalDose' in MODALITY_TAGS['PT']

def test_all_tags_exist()-> None:
    # Check that all tags in MODALITY_TAGS exist in pydicom
    for modality, tags in MODALITY_TAGS.items():
        for tag in tags:
            assert tag_exists(tag), (
                f"Tag {tag} not found in pydicom."
                f" Modality: {modality}"
                
            )