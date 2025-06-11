import pytest
from imgtools.utils import sanitize_file_name


class TestSanitizeFileName:
    """Test suite for the sanitize_file_name function."""

    def test_basic_valid_filenames(self):
        """Test that valid filenames remain unchanged - basic cases with various extensions."""
        assert sanitize_file_name("valid_filename.dcm") == "valid_filename.dcm"
        assert sanitize_file_name("file-name.txt") == "file-name.txt"
        assert sanitize_file_name("simple_file_name.py") == "simple_file_name.py"
        assert sanitize_file_name("MiXeD_CaSe.TXT") == "MiXeD_CaSe.TXT"
        assert sanitize_file_name("UPPERCASE.txt") == "UPPERCASE.txt"
        assert sanitize_file_name("lowercase.TXT") == "lowercase.TXT"

    def test_disallowed_characters_replacement(self):
        """Test that disallowed characters are properly replaced with underscores."""
        assert sanitize_file_name("file<>name:test?.dcm") == "file_name_test_.dcm"
        assert sanitize_file_name("file:name.txt") == "file_name.txt"
        assert sanitize_file_name("file*name?.txt") == "file_name_.txt"
        assert sanitize_file_name("a<b>c:d\"e\\f|g?h*i") == "a_b_c_d_e_f_g_h_i"
        assert sanitize_file_name("file::::name.txt") == "file_name.txt"

    def test_whitespace_handling(self):
        """Test handling of spaces and whitespace formatting in filenames."""
        # Simple space replacement
        assert sanitize_file_name("my file name.dcm") == "my_file_name.dcm"
        assert sanitize_file_name("file with spaces.txt") == "file_with_spaces.txt"
        # Padded spaces
        assert sanitize_file_name("   padded   filename.txt") == "padded_filename.txt"
        # Hyphen with spaces
        assert sanitize_file_name("file - name.dcm") == "file-name.dcm"
        assert sanitize_file_name("file - name - test.dcm") == "file-name-test.dcm"
        assert sanitize_file_name("file -name.dcm") == "file_-name.dcm"  # Single space not replaced
        assert sanitize_file_name("file- name.dcm") == "file-_name.dcm"  # Single space not replaced
        assert sanitize_file_name('UTERUS - 1 - SE') == 'UTERUS-1-SE'
        assert sanitize_file_name('UTERUS - 2') == 'UTERUS-2'
        # Multiple spaces and special chars
        assert sanitize_file_name("  file   -  name.txt") == "file_-_name.txt"

    def test_input_validation(self):
        """Test input validation - empty strings and non-string inputs should raise AssertionError."""
        with pytest.raises(AssertionError):
            sanitize_file_name("")
        
        with pytest.raises(AssertionError):
            sanitize_file_name(None)
            
        with pytest.raises(AssertionError):
            sanitize_file_name(123)
            
        with pytest.raises(AssertionError):
            sanitize_file_name(["file_name.dcm"])

    def test_path_handling(self):
        """Test handling of path-like filenames where forward slashes should be preserved."""
        assert sanitize_file_name("path/to/file.txt") == "path/to/file.txt"
        assert sanitize_file_name("/root/path/file.txt") == "/root/path/file.txt"
        assert sanitize_file_name("path/with:<>|?*/issues.txt") == "path/with_/issues.txt"
        # Test consecutive slashes
        assert sanitize_file_name("path///to////file.txt") == "path///to////file.txt"

    def test_unicode_and_special_characters(self):
        """Test handling of unicode, control characters, and other special characters."""
        # Unicode characters
        assert sanitize_file_name("résumé.pdf") == "résumé.pdf"
        assert sanitize_file_name("文件名.txt") == "文件名.txt"
        assert sanitize_file_name("üñîçódè<>*:?.txt") == "üñîçódè_.txt"
        
        # Control characters (0x00-0x1f)
        assert sanitize_file_name("file\x01name\x1F.txt") == "file_name_.txt"
        assert sanitize_file_name("\x00\x01\x02file.txt") == "file.txt"
        assert sanitize_file_name("file.txt\x1d\x1e\x1f") == "file.txt"
        
    def test_edge_cases(self):
        """Test edge cases including leading/trailing characters, complex patterns, and extreme cases."""
        # Leading and trailing characters
        assert sanitize_file_name("...file.txt") == "...file.txt"
        assert sanitize_file_name("file.txt...") == "file.txt..."
        assert sanitize_file_name(">>file.txt<<") == "file.txt"
        assert sanitize_file_name("   <>:?*|   valid.txt   ") == "__valid.txt"
        
        # Multiple periods
        assert sanitize_file_name("file.name.with.dots.txt") == "file.name.with.dots.txt"
        assert sanitize_file_name("..hidden.file") == "..hidden.file"
        assert sanitize_file_name("file....name") == "file....name"
        
        # All disallowed characters
        assert sanitize_file_name("<>|?*:\\\"") == ""
        assert sanitize_file_name("<>file<>") == "file"
        
        # Very long filename
        long_name = "a" * 1000
        assert sanitize_file_name(long_name) == long_name
        
        # File with extension but only disallowed characters in name
        assert sanitize_file_name("<>:|?*.txt") == ".txt"
