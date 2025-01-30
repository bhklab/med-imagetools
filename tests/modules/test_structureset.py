from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import SimpleITK as sitk

from imgtools.modules.structureset import (
    StructureSet,
)  # Replace `your_module` with the actual module name


@pytest.fixture
def roi_points():
    """Fixture for mock ROI points."""
    return {
        "GTV": [np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])],
        "PTV": [np.array([[2.0, 2.0, 2.0], [3.0, 3.0, 3.0]])],
        "CTV_0": [np.array([[4.0, 4.0, 4.0], [5.0, 5.0, 5.0]])],
        "CTV_1": [np.array([[6.0, 6.0, 6.0], [7.0, 7.0, 7.0]])],
        "CTV_2": [np.array([[8.0, 8.0, 8.0], [9.0, 9.0, 9.0]])],
        "ExtraROI": [np.array([[10.0, 10.0, 10.0], [11.0, 11.0, 11.0]])],
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
        (
            [["GTV", "PTV"], "CTV.*"],
            False,
            False,
            {"GTV": 0, "PTV": 0, "CTV_0": 1, "CTV_1": 1, "CTV_2": 1},
        ),
        # Case 8: Grouped patterns with separate labels for regex matches
        # ([["GTV", "PTV"], "CTV.*"], False, True, {"GTV": 0, "PTV": 0, "CTV_0": 1, "CTV_1": 2, "CTV_2": 3}),
    ],
)
def test_assign_labels(
    names, roi_select_first, roi_separate, expected, roi_points
) -> None:
    """Test _assign_labels method with various cases."""
    structure_set = StructureSet(roi_points)
    result = structure_set._assign_labels(
        names, roi_select_first, roi_separate
    )
    assert result == expected


# Parametrized tests for complex scenarios with intricate patterns
@pytest.mark.parametrize(
    "names, roi_select_first, roi_separate, expected",
    [
        # Case 1: Complex regex patterns with partial matches
        (
            ["G.*", "C.*1", "Extra.*"],
            False,
            False,
            {"GTV": 0, "CTV_1": 1, "ExtraROI": 2},
        ),
        # Case 2: Nested regex patterns with grouped and separated labels
        (
            [["GTV", "CTV.*"], "P.*", "Extra.*"],
            False,
            False,
            {
                "GTV": 0,
                "CTV_0": 0,
                "CTV_1": 0,
                "CTV_2": 0,
                "PTV": 1,
                "ExtraROI": 2,
            },
        ),
        # ([["GTV", "CTV.*"], "P.*", "Extra.*"], False, True, {"GTV": 0, "CTV_0_0": 1, "CTV_1_1": 2, "CTV_2_2": 3, "PTV": 4, "ExtraROI": 5}),
        # Case 3: Regex patterns that match all ROIs
        (
            [".*"],
            False,
            False,
            {
                "GTV": 0,
                "PTV": 0,
                "CTV_0": 0,
                "CTV_1": 0,
                "CTV_2": 0,
                "ExtraROI": 0,
            },
        ),
        # ([".*"], False, True, {"GTV_0": 0, "PTV_1": 1, "CTV_0_2": 2, "CTV_1_3": 3, "CTV_2_4": 4, "ExtraROI_5": 5}),
        # Case 4: Overlapping regex patterns
        (
            ["G.*", "C.*", "Extra.*"],
            False,
            False,
            {"GTV": 0, "CTV_0": 1, "CTV_1": 1, "CTV_2": 1, "ExtraROI": 2},
        ),
        # (["G.*", "C.*", "Extra.*"], False, True, {"GTV": 0, "CTV_0_0": 1, "CTV_1_1": 2, "CTV_2_2": 3, "ExtraROI_3": 4}),
        # Case 5: No matches for given patterns
        pytest.param(
            ["NonExistent.*"],
            False,
            False,
            {},
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        # Case 6: Conflicting options (should raise an error)
        # pytest.param(["G.*"], True, True, None, marks=pytest.mark.xfail(raises=ValueError)),
    ],
)
def test_assign_labels_complex(
    names, roi_select_first, roi_separate, expected, roi_points
) -> None:
    """Test _assign_labels method with complex scenarios."""
    structure_set = StructureSet(roi_points)
    result = structure_set._assign_labels(
        names, roi_select_first, roi_separate
    )
    assert result == expected


def test_assign_labels_invalid(roi_points) -> None:
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
        structure_set._assign_labels(
            ["G.*"], roi_select_first=True, roi_separate=True
        )


def test_init(roi_points, metadata) -> None:
    """Test StructureSet initialization."""
    structure_set = StructureSet(roi_points, metadata)
    assert structure_set.roi_points == roi_points
    assert structure_set.metadata == metadata

    # Test default metadata
    structure_set_no_metadata = StructureSet(roi_points)
    assert structure_set_no_metadata.metadata == {}


@patch("imgtools.modules.structureset.dcmread")
def test_from_dicom_rtstruct(mock_dcmread) -> None:
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
    mock_rtstruct.Modality = "RTSTRUCT"
    mock_dcmread.return_value = mock_rtstruct

    structure_set = StructureSet.from_dicom_rtstruct("dummy")
    # Assert the results
    assert "GTV" in structure_set.roi_points
    assert "PTV" in structure_set.roi_points
    assert len(structure_set.roi_points["GTV"]) == 1
    assert len(structure_set.roi_points["PTV"]) == 1


def test_rtstruct_to_segmentation(roi_points, metadata) -> None:
    """Test rtstruct_to_segmentation method with mocked ROI points."""
    structure_set = StructureSet(roi_points, metadata)
    # reference sitk_image
    ref_image = sitk.Image(10, 10, 10, sitk.sitkFloat32)

    seg_images = structure_set.to_segmentation(
        reference_image=ref_image, roi_names=["GTV", "PTV"]
    )

    assert seg_images is not None

    raw_roi_names = seg_images.raw_roi_names

    assert "GTV" in raw_roi_names
    assert "PTV" in raw_roi_names
    assert list(seg_images.roi_indices.keys()) == ["GTV", "PTV"]

    seg_images2 = structure_set.to_segmentation(
        reference_image=ref_image, roi_names="GTV"
    )

    assert seg_images2 is not None

    assert "GTV" in seg_images2.raw_roi_names
    assert "PTV" not in seg_images2.raw_roi_names

    assert seg_images2.get_label(name="GTV") is not None

    assert list(seg_images2.roi_indices.keys()) == ["GTV"]

    assert repr(seg_images2) == "<Segmentation with ROIs: {'GTV': 1}>"
