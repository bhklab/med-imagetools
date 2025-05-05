import pytest
from imgtools.utils import sanitize_file_name  # Adjust the import based on your module name


class TestSanitizeFileName:
    def test_valid_filename_no_changes(self):
        """Test that a valid filename remains unchanged."""
        assert sanitize_file_name("valid_filename.dcm") == "valid_filename.dcm"

    def test_disallowed_characters(self):
        """Test that disallowed characters are replaced with underscores."""
        assert sanitize_file_name("file<>name:/test?.dcm") == "file_name_test_.dcm"

    def test_spaces_replacement(self):
        """Test that spaces are replaced with underscores."""
        assert sanitize_file_name("my file name.dcm") == "my_file_name.dcm"

    def test_multiple_underscores(self):
        """Test that multiple consecutive underscores are replaced with a single underscore."""
        assert sanitize_file_name("file<>name  test:/??.dcm") == "file_name_test_.dcm"

    def test_empty_string(self):
        """Test that an empty string raises an assertion error."""
        with pytest.raises(AssertionError):
            sanitize_file_name("")

    def test_non_string_input(self):
        """Test that non-string inputs raise an assertion error."""
        with pytest.raises(AssertionError):
            sanitize_file_name(None)
        with pytest.raises(AssertionError):
            sanitize_file_name(123)
        with pytest.raises(AssertionError):
            sanitize_file_name(["file_name.dcm"])

    def test_control_characters(self):
        """Test that control characters are removed."""
        assert sanitize_file_name("file\x00\x1fname.dcm") == "file_name.dcm"

    def test_edge_case_long_string(self):
        """Test a long filename to ensure it sanitizes correctly."""
        long_filename = "a" * 255 + "<>:\"/\\|?*.dcm"
        expected = "a" * 255 + "_.dcm"
        assert sanitize_file_name(long_filename) == expected

    def test_edge_case_trailing_underscore(self):
        """Test that sanitized filenames don't end with unnecessary underscores."""
        assert sanitize_file_name("file<>:name?/") == "file_name"

    def test_special_characters_with_spaces(self):
        """Test a mix of special characters and spaces."""
        assert sanitize_file_name("my file<>name:/ test?.dcm") == "my_file_name_test_.dcm"

    def test_no_extension(self):
        """Test filenames without extensions."""
        assert sanitize_file_name("file<>name:/test") == "file_name_test"

    def test_only_special_characters(self):
        """Test filenames that consist only of disallowed characters."""
        assert sanitize_file_name("<>:/filename\\|?*") == "filename"

    def test_leading_trailing_spaces(self):
        """Test filenames with leading and trailing spaces."""
        assert sanitize_file_name("  my file name  .dcm") == "my_file_name_.dcm"