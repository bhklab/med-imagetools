import datetime
import tempfile
from pathlib import Path

import pytest
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.errors import InvalidDicomError
from pydicom.uid import UID, ExplicitVRLittleEndian

from imgtools.dicom.sort.utils import read_tags, sanitize_file_name, truncate_uid


@pytest.fixture(scope='module')
def dicom_test_file():
    """Pytest fixture to create a DICOM file for testing."""
    ds = Dataset()
    # Patient and instance-related metadata
    ds.PatientName = 'Test^Firstname'
    ds.PatientID = '123456'

    # Dates and times
    datetime.datetime.now()
    ds.ContentDate = '20021114'
    ds.ContentTime = '111131'  # Updated time format

    # Other metadata
    ds.SpecificCharacterSet = 'ISO_IR 100'
    ds.ImageType = ['ORIGINAL', 'PRIMARY', 'AXIAL']
    ds.StudyDate = '20021114'
    ds.SeriesDate = '20021114'
    ds.AcquisitionDate = '20021114'
    ds.StudyTime = '105444'
    ds.SeriesTime = '110039'
    ds.AcquisitionTime = '110234.982284'
    ds.Modality = 'CT'
    ds.Manufacturer = 'GE MEDICAL SYSTEMS'
    ds.StudyDescription = 'CT ABD & PELVIS W/O &'
    ds.SeriesDescription = '2.5SOFT + 30%ASIR'
    ds.ManufacturerModelName = 'LightSpeed VCT'
    ds.SeriesInstanceUID = UID('1.2.840.113619.2.55.3.604688.12345678.1234567890')
    ds.StudyInstanceUID = UID('1.2.840.113619.2.55.3.604688.98765432.9876543210')
    # File meta information
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = UID('1.2.840.10008.5.1.4.1.1.2')
    file_meta.MediaStorageSOPInstanceUID = UID(
        '1.3.6.1.4.1.14519.5.2.1.1706.4016.292639580813240923432069920621'
    )
    file_meta.ImplementationClassUID = UID('1.2.3.4')
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds.file_meta = file_meta

    # Create a temporary file
    temp_file = Path(tempfile.NamedTemporaryFile(suffix='.dcm', delete=False).name)
    ds.save_as(temp_file, write_like_original=False)

    yield temp_file

    # Cleanup
    temp_file.unlink()


class TestReadTags:
    def test_read_tags_with_main_metadata(self, dicom_test_file) -> None:
        tags = [
            'PatientName',
            'PatientID',
            'ContentDate',
            'ContentTime',
            'SpecificCharacterSet',
            'StudyDate',
            'SeriesDate',
            'AcquisitionDate',
            'StudyTime',
            'SeriesTime',
            'AcquisitionTime',
            'Modality',
            'Manufacturer',
            'StudyDescription',
            'SeriesDescription',
            'ManufacturerModelName',
        ]
        result = read_tags(file=dicom_test_file, tags=tags, truncate=True, sanitize=True)
        assert result['PatientName'] == sanitize_file_name('Test^Firstname')
        assert result['PatientID'] == sanitize_file_name('123456')
        assert result['ContentDate'] == sanitize_file_name('20021114')
        assert result['ContentTime'] == sanitize_file_name('111131')
        assert result['SpecificCharacterSet'] == sanitize_file_name('ISO_IR 100')
        assert result['StudyDate'] == sanitize_file_name('20021114')
        assert result['SeriesDate'] == sanitize_file_name('20021114')
        assert result['AcquisitionDate'] == sanitize_file_name('20021114')
        assert result['StudyTime'] == sanitize_file_name('105444')
        assert result['SeriesTime'] == sanitize_file_name('110039')
        assert result['AcquisitionTime'] == sanitize_file_name('110234.982284')
        assert result['Modality'] == sanitize_file_name('CT')
        assert result['Manufacturer'] == sanitize_file_name('GE MEDICAL SYSTEMS')
        assert result['StudyDescription'] == sanitize_file_name('CT ABD & PELVIS W/O &')
        assert result['SeriesDescription'] == sanitize_file_name('2.5SOFT + 30%ASIR')
        assert result['ManufacturerModelName'] == sanitize_file_name('LightSpeed VCT')

    def test_read_tags_with_empty_tags(self, dicom_test_file) -> None:
        tags = []
        result = read_tags(file=dicom_test_file, tags=tags, truncate=True, sanitize=True)
        assert result == {}

    def test_read_tags_with_nonexistent_tags(self, dicom_test_file) -> None:
        tags = ['NonexistentTag']
        with pytest.raises(ValueError):
            read_tags(file=dicom_test_file, tags=tags, truncate=True, sanitize=True)

    def test_read_tags_with_partial_metadata(self, dicom_test_file) -> None:
        tags = ['PatientName', 'Modality', 'NonexistentTag']
        with pytest.raises(ValueError):
            read_tags(file=dicom_test_file, tags=tags, truncate=True, sanitize=True)
        # assert result['PatientName'] == 'Test^Firstname'
        # assert result['Modality'] == 'CT'
        # assert 'NonexistentTag' not in result

    def test_read_tags_with_truncate_false(self, dicom_test_file) -> None:
        tags = ['SeriesInstanceUID']
        result = read_tags(file=dicom_test_file, tags=tags, truncate=False, sanitize=True)
        assert result['SeriesInstanceUID'] == '1.2.840.113619.2.55.3.604688.12345678.1234567890'

    def test_read_tags_with_sanitize_false(self, dicom_test_file) -> None:
        tags = ['StudyDescription']
        result = read_tags(file=dicom_test_file, tags=tags, truncate=True, sanitize=False)
        assert result['StudyDescription'] == 'CT ABD & PELVIS W/O &'

    def test_none_file(self) -> None:
        with pytest.raises(AssertionError):
            read_tags(file=None, tags=['PatientID'], truncate=True, sanitize=True)

    def test_invalid_dicom_file(self) -> None:
        inv_file = Path('invalid.dcm')
        inv_file.touch()
        with pytest.raises(InvalidDicomError):
            read_tags(file=Path(inv_file), tags=['PatientID'], truncate=True, sanitize=True)


class TestTruncateUid:
    def test_truncate_uid_with_default_last_digits(self) -> None:
        uid = '1.2.840.10008.1.2.1'
        result = truncate_uid(uid)
        assert result == '1.2.1'

    def test_truncate_uid_with_custom_last_digits(self) -> None:
        uid = '1.2.840.10008.1.2.1'
        result = truncate_uid(uid, last_digits=10)
        assert result == '0008.1.2.1'

    def test_truncate_uid_with_short_uid(self) -> None:
        uid = '12345'
        result = truncate_uid(uid, last_digits=10)
        assert result == '12345'

    def test_truncate_uid_with_zero_last_digits(self) -> None:
        uid = '1.2.840.10008.1.2.1'
        result = truncate_uid(uid, last_digits=0)
        assert result == '1.2.840.10008.1.2.1'

    def test_truncate_uid_with_negative_last_digits(self) -> None:
        uid = '1.2.840.10008.1.2.1'
        result = truncate_uid(uid, last_digits=-5)
        assert result == '1.2.840.10008.1.2.1'
