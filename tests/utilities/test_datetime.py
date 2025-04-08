import pytest
from datetime import date, time, datetime
from imgtools.utils.date_time import parse_datetime, parse_dicom_date, parse_dicom_time

class TestParseDateTime:
    def test_empty_value(self):
        """Test handling of empty values."""
        assert parse_datetime("AnyKey", "") == 0
        assert parse_datetime("AnyKey", "none") == 0
        assert parse_datetime("AnyKey", "None") == 0

    def test_duration_fields(self):
        """Test parsing of duration fields."""
        duration_fields = [
            "EchoTime",
            "RepetitionTime",
            "InversionTime",
            "FrameReferenceTime",
            "FrameTime",
            "AcquisitionDuration",
            "ExposureTime",
        ]
        
        for field in duration_fields:
            # Test integer value
            assert parse_datetime(field, "10") == 10.0
            # Test float value
            assert parse_datetime(field, "10.5") == 10.5
    
    def test_duration_field_error(self):
        """Test error handling for invalid duration field values."""
        with pytest.raises(ValueError, match="Failed to parse duration field EchoTime='abc' as float"):
            parse_datetime("EchoTime", "abc")
    
    def test_clock_fields(self):
        """Test parsing of clock-style time fields."""
        clock_fields = [
            "AcquisitionTime",
            "ContentTime",
            "InstanceCreationTime",
            "SeriesTime",
            "StudyTime",
            "StructureSetTime",
        ]
        
        expected_time = time(14, 30, 15)
        for field in clock_fields:
            assert parse_datetime(field, "143015") == expected_time
            
        # Test with milliseconds
        expected_time_ms = time(14, 30, 15, 500000)
        for field in clock_fields:
            assert parse_datetime(field, "143015.5") == expected_time_ms
    
    def test_date_fields(self):
        """Test parsing of date fields."""
        expected_date = date(2023, 10, 15)
        assert parse_datetime("StudyDate", "20231015") == expected_date
        assert parse_datetime("SeriesDate", "20231015") == expected_date
        assert parse_datetime("AcquisitionDate", "20231015") == expected_date
    
    def test_time_fields(self):
        """Test parsing of time fields with 'Time' in key name."""
        expected_time = time(14, 30, 15)
        assert parse_datetime("CustomTime", "143015") == expected_time
        
        expected_time_ms = time(14, 30, 15, 500000)
        assert parse_datetime("OtherTime", "143015.5") == expected_time_ms
    
    def test_unknown_key_fallback(self):
        """Test fallback to date parsing for unknown keys."""
        expected_date = date(2023, 10, 15)
        assert parse_datetime("UnknownKey", "20231015") == expected_date
    
    def test_unknown_key_error(self):
        """Test error handling for unknown keys with invalid values."""
        with pytest.raises(ValueError, match="Unknown DICOM key: 'UnknownKey'"):
            parse_datetime("UnknownKey", "invalid")
    
    def test_failed_date_parsing(self):
        """Test error handling for failed date parsing."""
        with pytest.raises(ValueError, match="Failed to parse StudyDate='2023-10-15'"):
            parse_datetime("StudyDate", "2023-10-15")
        
        with pytest.raises(ValueError, match="Failed to parse SeriesDate='1234'"):
            parse_datetime("SeriesDate", "1234")
            
    def test_failed_time_parsing(self):
        """Test error handling for failed time parsing."""
        with pytest.raises(ValueError, match="Failed to parse StudyTime='xyz'"):
            parse_datetime("StudyTime", "xyz")

    def test_parse_dicom_date_validation(self):
        """Test validation in parse_dicom_date function."""
        # Test incorrect length
        ok, msg = parse_dicom_date("123456")
        assert ok is False
        assert "Expected 8-digit date string" in msg
        
        # Test non-digit characters
        ok, msg = parse_dicom_date("2023/010")
        assert ok is False
        assert "Non-digit characters in date" in msg
        
        # Test invalid date
        ok, msg = parse_dicom_date("20231345")
        assert ok is False
        assert "Failed to parse date" in msg
        
        # Test valid date
        ok, result = parse_dicom_date("20231015")
        assert ok is True
        assert result == date(2023, 10, 15)
        
    def test_parse_dicom_time_validation(self):
        """Test validation in parse_dicom_time function."""
        # Test no digits
        ok, msg = parse_dicom_time("abc")
        assert ok is False
        assert "No digits found in time" in msg
        
        # Test valid time without milliseconds
        ok, result = parse_dicom_time("143015")
        assert ok is True
        assert result == time(14, 30, 15)
        
        # Test valid time with milliseconds
        ok, result = parse_dicom_time("143015.5")
        assert ok is True
        assert result == time(14, 30, 15, 500000)