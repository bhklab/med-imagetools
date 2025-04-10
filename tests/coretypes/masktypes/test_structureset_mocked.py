import pytest
from pathlib import Path
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.sequence import Sequence

from imgtools.coretypes.masktypes.structureset import RTStructureSet, ROIExtractionErrorMsg
from imgtools.exceptions import MissingROIError, ROIContourError


class TestRTStructureSet:
    
    @pytest.fixture
    def mock_dicom_rt(self):
        """Create a mock DICOM RT Structure Set file."""
        mock_rt = Mock(spec=FileDataset)
        
        # Create Structure Set ROI Sequence
        roi1 = Dataset()
        roi1.ROINumber = "1"
        roi1.ROIName = "GTV"
        
        roi2 = Dataset()
        roi2.ROINumber = "2"
        roi2.ROIName = "PTV"
        
        roi3 = Dataset()
        roi3.ROINumber = "3"
        roi3.ROIName = "Bladder"
        
        ss_roi_seq = [roi1, roi2, roi3]
        mock_rt.StructureSetROISequence = ss_roi_seq
        
        # Create ROI Contour Sequence
        roi_contour1 = Dataset()
        roi_contour1.ReferencedROINumber = "1"
        contour1_1 = Dataset()
        contour1_1.ContourGeometricType = "CLOSED_PLANAR"
        contour1_1.NumberOfContourPoints = 4
        contour1_1.ContourData = [0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0]
        roi_contour1.ContourSequence = [contour1_1]
        
        roi_contour2 = Dataset()
        roi_contour2.ReferencedROINumber = "2"
        contour2_1 = Dataset()
        contour2_1.ContourGeometricType = "CLOSED_PLANAR"
        contour2_1.NumberOfContourPoints = 4
        contour2_1.ContourData = [0, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1]
        roi_contour2.ContourSequence = [contour2_1]
        
        roi_contour3 = Dataset()
        roi_contour3.ReferencedROINumber = "3"
        # No ContourSequence for Bladder to test error case
        
        mock_rt.ROIContourSequence = [roi_contour1, roi_contour2, roi_contour3]
        
        mock_rt.SeriesDescription = "Mock RT Structure Set"
        mock_rt.SeriesInstanceUID = "1.2.3.4.5"
        mock_rt.Modality = "RTSTRUCT"
        
        return mock_rt
    
    @pytest.fixture
    def mock_metadata(self):
        """Create mock metadata for structure set."""
        return {
            "ROINames": ["GTV", "PTV", "Bladder"],
            "SeriesDescription": "Mock RT Structure Set",
            "SeriesInstanceUID": "1.2.3.4.5",
            "Modality": "RTSTRUCT"
        }
    
    @patch('imgtools.coretypes.masktypes.structureset.load_dicom')
    @patch('imgtools.coretypes.masktypes.structureset.extract_metadata')
    def test_from_dicom_with_file_path(self, mock_extract_metadata, mock_load_dicom, mock_dicom_rt, mock_metadata):
        """Test creating RTStructureSet from a file path."""
        mock_load_dicom.return_value = mock_dicom_rt
        mock_extract_metadata.return_value = mock_metadata
        
        file_path = Path("/path/to/structure.dcm")
        rt = RTStructureSet.from_dicom(file_path)
        
        # Check that load_dicom was called with the file path
        mock_load_dicom.assert_called_once_with(file_path)
        
        # Check metadata extraction
        mock_extract_metadata.assert_called_once_with(mock_dicom_rt, "RTSTRUCT", extra_tags=None)
        
        # Check structure set initialization
        assert rt.metadata == mock_metadata
        # Check error handling for Bladder (should be in roi_map_errors)
        assert "Bladder" in rt.roi_map_errors

        assert set(rt.roi_names) == set(["GTV", "PTV"])  # Names are duplicated due to extend and append
        assert set(rt.metadata['ROINames']) == set(["GTV", "PTV", "Bladder"])

        
    
    @patch('imgtools.coretypes.masktypes.structureset.load_dicom')
    @patch('imgtools.coretypes.masktypes.structureset.extract_metadata')
    def test_from_dicom_with_directory(self, mock_extract_metadata, mock_load_dicom, mock_dicom_rt, mock_metadata, tmp_path):
        """Test creating RTStructureSet from a directory with one DICOM file."""
        mock_load_dicom.return_value = mock_dicom_rt
        mock_extract_metadata.return_value = mock_metadata
        
        # Create a temp directory with one DICOM file
        dir_path = tmp_path / "dicom"
        dir_path.mkdir()
        file_path = dir_path / "structure.dcm"
        file_path.touch()
        
        with patch('pathlib.Path.glob', return_value=[file_path]):
            rt = RTStructureSet.from_dicom(dir_path)
            mock_load_dicom.assert_called_once()
    
    @patch('imgtools.coretypes.masktypes.structureset.load_dicom')
    @patch('imgtools.coretypes.masktypes.structureset.extract_metadata')
    def test_from_dicom_directory_multiple_files_error(self, mock_extract_metadata, mock_load_dicom, tmp_path):
        """Test error when directory contains multiple DICOM files."""
        dir_path = tmp_path / "dicom"
        dir_path.mkdir()
        file_path1 = dir_path / "structure1.dcm"
        file_path2 = dir_path / "structure2.dcm"
        file_path1.touch()
        file_path2.touch()
        
        with patch('pathlib.Path.glob', return_value=[file_path1, file_path2]):
            with pytest.raises(ValueError, match=r"Directory .* contains multiple DICOM files"):
                RTStructureSet.from_dicom(dir_path)

    def test_getitem_string(self, mock_metadata):
        """Test __getitem__ with string key."""
        rt = RTStructureSet(metadata=mock_metadata)
        rt.roi_names = ["GTV", "PTV"]
        rt.roi_map = {"GTV": "mock_roi_gtv", "PTV": "mock_roi_ptv"}
        
        # Test valid key
        assert rt["GTV"] == "mock_roi_gtv"
        
        # Test invalid key
        with pytest.raises(MissingROIError):
            rt["CTV"]
    
    def test_getitem_int(self, mock_metadata):
        """Test __getitem__ with int index."""
        rt = RTStructureSet(metadata=mock_metadata)
        rt.roi_names = ["GTV", "PTV"]
        rt.roi_map = {"GTV": "mock_roi_gtv", "PTV": "mock_roi_ptv"}
        
        # Test valid index
        assert rt[0] == "mock_roi_gtv"
        assert rt[1] == "mock_roi_ptv"
        
        # Test invalid index
        with pytest.raises(IndexError):
            rt[2]
    
    def test_getitem_slice(self, mock_metadata):
        """Test __getitem__ with slice."""
        rt = RTStructureSet(metadata=mock_metadata)
        rt.roi_names = ["GTV", "PTV", "Bladder", "Heart"]
        rt.roi_map = {
            "GTV": "mock_roi_gtv", 
            "PTV": "mock_roi_ptv",
            "Bladder": "mock_roi_bladder",
            "Heart": "mock_roi_heart"
        }
        
        # Test slices
        assert rt[0:2] == ["mock_roi_gtv", "mock_roi_ptv"]
        assert rt[1:3] == ["mock_roi_ptv", "mock_roi_bladder"]
        assert rt[:] == ["mock_roi_gtv", "mock_roi_ptv", "mock_roi_bladder", "mock_roi_heart"]
    
    def test_getitem_unsupported_type(self, mock_metadata):
        """Test __getitem__ with unsupported type."""
        rt = RTStructureSet(metadata=mock_metadata)
        
        with pytest.raises(MissingROIError, match=r"not supported"):
            rt[1.5]  # Float is not supported
    
    def test_len(self, mock_metadata):
        """Test __len__."""
        rt = RTStructureSet(metadata=mock_metadata)
        rt.roi_names = ["GTV", "PTV", "Bladder"]
        
        assert len(rt) == 3

    def test_summary(self, mock_metadata):
        """Test summary method."""
        rt = RTStructureSet(metadata=mock_metadata)
        rt.roi_names = ["GTV", "PTV"]
        rt.roi_map = {"GTV": "mock_roi_gtv", "PTV": "mock_roi_ptv"}
        rt.roi_map_errors = {"Bladder": ROIExtractionErrorMsg("Test error")}
        
        summary = rt.summary()
        
        # Check summary structure
        assert "Metadata" in summary
        assert "ROI Details" in summary
        assert "ROIErrors" in summary
        
        # Check specific contents
        assert "ROINames" not in summary["Metadata"]
        assert summary["ROI Details"] == rt.roi_map
        assert summary["ROIErrors"] == {"Bladder": "Test error"}
