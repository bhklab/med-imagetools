from pathlib import Path

import pytest
from rich.tree import Tree
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from imgtools.dicom.utils import find_dicoms

# from imgtools.sort import lookup_tag, similar_tags, tag_exists
# from imgtools.sort.exceptions import InvalidPatternError, SorterBaseError
# from imgtools.sort.sorter_base import SorterBase
from imgtools.dicom import lookup_tag, similar_tags, tag_exists, find_dicoms
########################################################################
# Test Helpers
########################################################################


@pytest.fixture
def temp_dir_with_files():
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Create dummy DICOM files
        (temp_path / "file1.dcm").touch()
        (temp_path / "file2.dcm").touch()
        # Create a subdirectory with more DICOM files
        sub_dir = temp_path / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file3.dcm").touch()
        (sub_dir / "file4.dcm").touch()
        yield temp_path


class TestFindDicoms:
    def test_non_recursive_no_header_check(self, temp_dir_with_files):
        result = find_dicoms(temp_dir_with_files, recursive=False, check_header=False)
        assert len(result) == 2
        assert all(file.suffix == ".dcm" for file in result)

    def test_recursive_no_header_check(self, temp_dir_with_files):
        result = find_dicoms(temp_dir_with_files, recursive=True, check_header=False)
        assert len(result) == 4
        assert all(file.suffix == ".dcm" for file in result)

    def test_non_recursive_with_header_check(self, temp_dir_with_files, mocker):
        mocker.patch("imgtools.dicom.utils.is_dicom", return_value=True)
        result = find_dicoms(temp_dir_with_files, recursive=False, check_header=True)
        assert len(result) == 2
        assert all(file.suffix == ".dcm" for file in result)

    def test_recursive_with_header_check(self, temp_dir_with_files, mocker):
        mocker.patch("imgtools.dicom.utils.is_dicom", return_value=True)
        result = find_dicoms(temp_dir_with_files, recursive=True, check_header=True)
        assert len(result) == 4
        assert all(file.suffix == ".dcm" for file in result)

    def test_search_with_specific_extension(self, temp_dir_with_files):
        (temp_dir_with_files / "file5.txt").touch()
        result = find_dicoms(
            temp_dir_with_files, recursive=True, check_header=False, extension="dcm"
        )
        assert len(result) == 4
        assert all(file.suffix == ".dcm" for file in result)


def test_similar_tags():
    """Test the similar_tags function."""
    incorrect_2_correct_mappings = {
        "PatientID": "Patient",
        "StudyInstanceUID": "StudyIntance",
        "SeriesInstanceUID": "SeriesIntance",
        "SOPInstanceUID": "SOPInstance",
        "Modality": "Modaliti",
        "SeriesDate": "SerieDate",
    }
    for correct, incorrect in incorrect_2_correct_mappings.items():
        assert correct in similar_tags(incorrect)


def test_lookup_tag():
    """Test the lookup_tag function."""
    assert lookup_tag("PatientID") == "1048608"
    assert lookup_tag("PatientID", hex_format=True) == "0x100020"
    assert lookup_tag("invalid") is None


def test_tag_exists():
    """Test the tag_exists function."""
    assert tag_exists("PatientID")


########################################################################
# Helper classes
########################################################################


# class MockSorter(SorterBase):
#     """
#     A mock implementation of SorterBase for testing purposes.

#     This class implements `_create_highlighter` and `validate_keys`.
#     """

#     def _create_highlighter(self):
#         """
#         Create a simple highlighter for testing purposes.
#         """
#         from rich.highlighter import RegexHighlighter

#         class TestHighlighter(RegexHighlighter):
#             base_style = "example."
#             highlights = [
#                 r"%\((?P<Key>[a-zA-Z0-9_]+)\)s",
#                 r"(?P<ForwardSlash>/)",
#             ]

#         return TestHighlighter()

#     def validate_keys(self):
#         """
#         Perform a dummy validation. In this test case, all keys are valid unless they start with 'invalid'.
#         """
#         invalid_keys = {key for key in self.keys if key.startswith("invalid")}
#         if invalid_keys:
#             raise InvalidPatternError(f"Invalid keys found: {', '.join(invalid_keys)}")


# def test_initialize_with_valid_pattern():
#     """Test initializing SorterBase with a valid pattern."""
#     sorter = MockSorter("%ParentDir/%SubDir/{FileName}")
#     assert sorter.format == "%(ParentDir)s/%(SubDir)s/%(FileName)s"
#     assert sorter.keys == {"ParentDir", "SubDir", "FileName"}


# def test_initialize_with_empty_pattern():
#     """Test initializing SorterBase with an empty pattern."""
#     with pytest.raises(SorterBaseError):
#         MockSorter("")


# def test_initialize_with_invalid_pattern():
#     """Test initializing SorterBase with a pattern that has no placeholders."""
#     with pytest.raises(SorterBaseError):
#         MockSorter("ParentDir/SubDir/FileName")


# def test_tree_visualization():
#     """Test generating a tree visualization."""
#     sorter = MockSorter("%ParentDir/%SubDir/{FileName}")
#     try:
#         sorter.print_tree()
#     except SorterBaseError:
#         pytest.fail("print_tree() raised SorterBaseError unexpectedly.")


# def test_replace_key():
#     """Test replacing placeholders with formatted keys."""
#     sorter = MockSorter("%Dir/{File}")
#     formatted, keys = sorter.format, sorter.keys
#     assert formatted == "%(Dir)s/%(File)s"
#     assert keys == {"Dir", "File"}


# def test_validate_keys_with_valid_keys():
#     """Test validate_keys with all valid keys."""
#     sorter = MockSorter("%Dir/{File}")
#     try:
#         sorter.validate_keys()
#     except InvalidPatternError:
#         pytest.fail("validate_keys() raised InvalidPatternError unexpectedly.")


# def test_validate_keys_with_invalid_keys():
#     """Test validate_keys with invalid keys."""
#     sorter = MockSorter("%invalidKey/{validKey}")
#     with pytest.raises(InvalidPatternError, match="Invalid keys found: invalidKey"):
#         sorter.validate_keys()
