from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

# from imgtools.sort import lookup_tag, similar_tags, tag_exists
# from imgtools.sort.exceptions import InvalidPatternError, SorterBaseError
# from imgtools.sort.sorter_base import SorterBase
from imgtools.dicom import find_dicoms, lookup_tag, similar_tags, tag_exists
from imgtools.dicom.utils import find_dicoms

########################################################################
# Test Helpers
########################################################################


@pytest.fixture
def temp_dir_with_files():
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Create dummy DICOM files
        (temp_path / 'file1.dcm').touch()
        (temp_path / 'file2.dcm').touch()
        # Create a subdirectory with more DICOM files
        sub_dir = temp_path / 'subdir'
        sub_dir.mkdir()
        (sub_dir / 'file3.dcm').touch()
        (sub_dir / 'file4.dcm').touch()
        yield temp_path


class TestFindDicoms:
    def test_non_recursive_no_header_check(self, temp_dir_with_files) -> None:
        result = find_dicoms(temp_dir_with_files, recursive=False, check_header=False)
        assert len(result) == 2
        assert all(file.suffix == '.dcm' for file in result)

    def test_recursive_no_header_check(self, temp_dir_with_files) -> None:
        result = find_dicoms(temp_dir_with_files, recursive=True, check_header=False)
        assert len(result) == 4
        assert all(file.suffix == '.dcm' for file in result)

    def test_non_recursive_with_header_check(self, temp_dir_with_files, mocker) -> None:
        mocker.patch('imgtools.dicom.utils.is_dicom', return_value=True)
        result = find_dicoms(temp_dir_with_files, recursive=False, check_header=True)
        assert len(result) == 2
        assert all(file.suffix == '.dcm' for file in result)

    def test_recursive_with_header_check(self, temp_dir_with_files, mocker) -> None:
        mocker.patch('imgtools.dicom.utils.is_dicom', return_value=True)
        result = find_dicoms(temp_dir_with_files, recursive=True, check_header=True)
        assert len(result) == 4
        assert all(file.suffix == '.dcm' for file in result)

    def test_search_with_specific_extension(self, temp_dir_with_files) -> None:
        (temp_dir_with_files / 'file5.txt').touch()
        result = find_dicoms(
            temp_dir_with_files, recursive=True, check_header=False, extension='dcm'
        )
        assert len(result) == 4
        assert all(file.suffix == '.dcm' for file in result)

    def test_limit_results(self, temp_dir_with_files) -> None:
        result = find_dicoms(temp_dir_with_files, recursive=True, check_header=False, limit=2)
        assert len(result) == 2
        assert all(file.suffix == '.dcm' for file in result)

    def test_search_with_input(self, temp_dir_with_files) -> None:
        (temp_dir_with_files / 'scan1.dcm').touch()
        (temp_dir_with_files / 'scan2.dcm').touch()
        result = find_dicoms(
            temp_dir_with_files, recursive=True, check_header=False, search_input=['scan']
        )
        assert len(result) == 2
        assert all('scan' in file.name for file in result)

    def test_combined_options(self, temp_dir_with_files, mocker) -> None:
        mocker.patch('imgtools.dicom.utils.is_dicom', return_value=True)
        (temp_dir_with_files / 'scan1.dcm').touch()
        result = find_dicoms(
            temp_dir_with_files,
            recursive=True,
            check_header=True,
            extension='dcm',
            limit=3,
            search_input=['scan'],
        )
        assert len(result) == 1
        assert all(file.suffix == '.dcm' for file in result)
        assert all('scan' in file.name for file in result)


def test_similar_tags() -> None:
    """Test the similar_tags function."""
    incorrect_2_correct_mappings = {
        'PatientID': 'Patient',
        'StudyInstanceUID': 'StudyIntance',
        'SeriesInstanceUID': 'SeriesIntance',
        'SOPInstanceUID': 'SOPInstance',
        'Modality': 'Modaliti',
        'SeriesDate': 'SerieDate',
    }
    for correct, incorrect in incorrect_2_correct_mappings.items():
        assert correct in similar_tags(incorrect)


def test_lookup_tag() -> None:
    """Test the lookup_tag function."""
    assert lookup_tag('PatientID') == '1048608'
    assert lookup_tag('PatientID', hex_format=True) == '0x100020'
    assert lookup_tag('invalid') is None


def test_tag_exists() -> None:
    """Test the tag_exists function."""
    assert tag_exists('PatientID')
