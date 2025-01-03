import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from typing import Dict, List
from pydicom.dataset import Dataset
from imgtools.modules.structureset import StructureSet  # Replace `your_module` with the actual module name
import pathlib

@pytest.fixture
def modalities_path():
    curr_path = pathlib.Path(__file__).parent.parent.parent

    qc_path = pathlib.Path(curr_path, "data", "Head-Neck-PET-CT", "HN-CHUS-052")
    assert qc_path.exists(), "Dataset not found"
    
    path = {}
    path["CT"] = pathlib.Path(qc_path, "08-27-1885-CA ORL FDG TEP POS TX-94629/3.000000-Merged-06362").as_posix()
    path["RTSTRUCT"] = pathlib.Path(qc_path, "08-27-1885-OrophCB.0OrophCBTRTID derived StudyInstanceUID.-94629/Pinnacle POI-41418").as_posix()
    path["RTDOSE"] = pathlib.Path(qc_path, "08-27-1885-OrophCB.0OrophCBTRTID derived StudyInstanceUID.-94629/11376").as_posix()
    path["PT"] = pathlib.Path(qc_path, "08-27-1885-CA ORL FDG TEP POS TX-94629/532790.000000-LOR-RAMLA-44600").as_posix()
    return path

@pytest.fixture
def roi_points():
    """Fixture for mock ROI points."""
    return {
        "GTV": [np.array([[0, 0, 0], [1, 1, 1]])],
        "PTV": [np.array([[2, 2, 2], [3, 3, 3]])],
        "CTV_0": [np.array([[4, 4, 4], [5, 5, 5]])],
        "CTV_1": [np.array([[6, 6, 6], [7, 7, 7]])],
        "CTV_2": [np.array([[8, 8, 8], [9, 9, 9]])],
        "ExtraROI": [np.array([[10, 10, 10], [11, 11, 11]])],
    }

@pytest.fixture
def metadata():
    """Fixture for mock metadata."""
    return {"PatientName": "John Doe"}

# Parametrized tests for simple and moderately complex cases
@pytest.mark.parametrize(
    "names, roi_select_first, roi_separate, expected",
    [
        # Case 1: Default behavior with exact matches
        (["GTV", "PTV"], False, False, {"GTV": 0, "PTV": 1}),

        # Case 2: Regex matching
        (["GTV", "P.*"], False, False, {"GTV": 0, "PTV": 1}),

        # Case 3: Select only the first match for each pattern
        (["G.*", "P.*"], True, False, {"GTV": 0, "PTV": 1}),

        # Case 4: Separate matches for regex pattern
        (["P.*"], False, True, {"PTV": 0}),

        # Case 5: Regex pattern with multiple matches (consolidated labels)
        (["CTV.*"], False, False, {"CTV_0": 0, "CTV_1": 0, "CTV_2": 0}),

        # Case 6: Regex pattern with multiple matches (separate labels)
        (["CTV.*"], False, True, {"CTV_0": 0, "CTV_1": 0, "CTV_2": 0}),

        # Case 7: Grouped patterns
        ([["GTV", "PTV"], "CTV.*"], False, False, {"GTV": 0, "PTV": 0, "CTV_0": 1, "CTV_1": 1, "CTV_2": 1}),

        # Case 8: Grouped patterns with separate labels for regex matches
        # ([["GTV", "PTV"], "CTV.*"], False, True, {"GTV": 0, "PTV": 0, "CTV_0": 1, "CTV_1": 2, "CTV_2": 3}),
    ],
)
def test_assign_labels(names, roi_select_first, roi_separate, expected, roi_points):
    """Test _assign_labels method with various cases."""
    structure_set = StructureSet(roi_points)
    result = structure_set._assign_labels(names, roi_select_first, roi_separate)
    assert result == expected


# Parametrized tests for complex scenarios with intricate patterns
@pytest.mark.parametrize(
    "names, roi_select_first, roi_separate, expected",
    [
        # Case 1: Complex regex patterns with partial matches
        (["G.*", "C.*1", "Extra.*"], False, False, {"GTV": 0, "CTV_1": 1, "ExtraROI": 2}),

        # Case 2: Nested regex patterns with grouped and separated labels
        ([["GTV", "CTV.*"], "P.*", "Extra.*"], False, False, {"GTV": 0, "CTV_0": 0, "CTV_1": 0, "CTV_2": 0, "PTV": 1, "ExtraROI": 2}),
        # ([["GTV", "CTV.*"], "P.*", "Extra.*"], False, True, {"GTV": 0, "CTV_0_0": 1, "CTV_1_1": 2, "CTV_2_2": 3, "PTV": 4, "ExtraROI": 5}),

        # Case 3: Regex patterns that match all ROIs
        ([".*"], False, False, {"GTV": 0, "PTV": 0, "CTV_0": 0, "CTV_1": 0, "CTV_2": 0, "ExtraROI": 0}),
        # ([".*"], False, True, {"GTV_0": 0, "PTV_1": 1, "CTV_0_2": 2, "CTV_1_3": 3, "CTV_2_4": 4, "ExtraROI_5": 5}),

        # Case 4: Overlapping regex patterns
        (["G.*", "C.*", "Extra.*"], False, False, {"GTV": 0, "CTV_0": 1, "CTV_1": 1, "CTV_2": 1, "ExtraROI": 2}),
        # (["G.*", "C.*", "Extra.*"], False, True, {"GTV": 0, "CTV_0_0": 1, "CTV_1_1": 2, "CTV_2_2": 3, "ExtraROI_3": 4}),

        # Case 5: No matches for given patterns
        pytest.param(["NonExistent.*"], False, False, {}, marks=pytest.mark.xfail(raises=ValueError)),

        # Case 6: Conflicting options (should raise an error)
        # pytest.param(["G.*"], True, True, None, marks=pytest.mark.xfail(raises=ValueError)),
    ],
)
def test_assign_labels_complex(names, roi_select_first, roi_separate, expected, roi_points):
    """Test _assign_labels method with complex scenarios."""
    structure_set = StructureSet(roi_points)
    result = structure_set._assign_labels(names, roi_select_first, roi_separate)
    assert result == expected


def test_assign_labels_invalid(roi_points):
    """Test _assign_labels method with invalid inputs."""
    structure_set = StructureSet(roi_points)

    # Case: Empty names
    with pytest.raises(ValueError, match="The 'names' list cannot be empty."):
        structure_set._assign_labels([])

    # Case: Conflicting options
    with pytest.raises(
        ValueError,
        match="The options 'roi_select_first' and 'roi_separate' cannot both be True.",
    ):
        structure_set._assign_labels(["G.*"], roi_select_first=True, roi_separate=True)


def test_init(roi_points, metadata):
    """Test StructureSet initialization."""
    structure_set = StructureSet(roi_points, metadata)
    assert structure_set.roi_points == roi_points
    assert structure_set.metadata == metadata

    # Test default metadata
    structure_set_no_metadata = StructureSet(roi_points)
    assert structure_set_no_metadata.metadata == {}

@patch("imgtools.modules.structureset.dcmread")
def test_from_dicom_rtstruct(mock_dcmread):
    """Test from_dicom_rtstruct method with mocked DICOM file."""
    """Test from_dicom_rtstruct method with mocked DICOM file."""
    mock_rtstruct = MagicMock()
    mock_rtstruct.StructureSetROISequence = [
        MagicMock(ROIName="GTV"),
        MagicMock(ROIName="PTV"),
    ]
    mock_rtstruct.ROIContourSequence = [
        MagicMock(),
        MagicMock(),
    ]
    mock_rtstruct.ROIContourSequence[0].ContourSequence = [
        MagicMock(ContourData=[1.0, 2.0, 3.0])
    ]
    mock_rtstruct.ROIContourSequence[1].ContourSequence = [
        MagicMock(ContourData=[4.0, 5.0, 6.0])
    ]
    mock_dcmread.return_value = mock_rtstruct

    structure_set = StructureSet.from_dicom_rtstruct('dummy')
    # Assert the results
    assert "GTV" in structure_set.roi_points
    assert "PTV" in structure_set.roi_points
    assert len(structure_set.roi_points["GTV"]) == 1
    assert len(structure_set.roi_points["PTV"]) == 1
