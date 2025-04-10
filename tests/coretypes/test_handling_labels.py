from imgtools.coretypes.masktypes import (
    ROIMatcher,
    ROI_HANDLING,
    handle_roi_matching,
    ROIMatchResult,
    match_roi,
)
import pytest
from rich import print
###############################################################################
# Tests
###############################################################################
# parametrize the test function with different matcher inputs

@pytest.mark.parametrize(
    "roi_matching",
    [
        # Test with a list of strings
        (["GTV", "PTV", "CTV"]),
        # Test with a single string
        ("GTV"),
        # Test with None
        (None),
        # Test with an empty dictionary
        ({}),
        # Test with a dictionary of lists
        ({"GTV": ["GTV", "PTV"], "CTV": ["CTV", "PTV"]}),
        # Test with a dictionary of strings
        ({"GTV": "GTV", "PTV": "PTV"}),
    ],
)
def test_parse_matcher_dict(roi_matching):
    """Test parsing a dictionary matcher."""
    roimatcher = ROIMatcher(roi_map=roi_matching)
    result = roimatcher.roi_map
    # Check that the result is a dictionary
    assert isinstance(result, dict)
    
    assert len(result) > 0
    for key, value in result.items():
        assert isinstance(value, list)
        assert all(isinstance(v, str) for v in value)


@pytest.fixture
def roi_names():
    rois =  [
        "CTV_0", "CTV_1", "CTV_2",
        "ExtraROI", "ExtraROI2",
        "GTV 0", "GTVp",
        "PTV", "ptv x",
    ]
    return rois


@pytest.fixture
def roi_matching():
    return {
        "GTV": ["GTV.*"],
        "PTV": ["PTV.*"],
        "TV": ["GTV.*", "PTV.*", "CTV.*"],
        "extra": ["ExtraROI", "ExtraROI2"]
    }


@pytest.mark.parametrize(
    "strategy,expected_output",
    [
        (
            ROI_HANDLING.SEPARATE,
            [
                ("GTV", "GTV 0"), ("GTV", "GTVp"),
                ("PTV", "PTV"),  # <-- "ptv x" not included
                ("TV", "GTV 0"), ("TV", "GTVp"),  ("TV", "PTV"), ("TV", "CTV_0"), ("TV", "CTV_1"), ("TV", "CTV_2"),  # <-- "ptv x" excluded
                ("extra", "ExtraROI"), ("extra", "ExtraROI2")
            ]
        ),
        (
            ROI_HANDLING.MERGE,
            [
                ("GTV", ["GTV 0", "GTVp"]),
                ("PTV", ["PTV"]),  # <-- "ptv x" excluded
                ("TV", ["GTV 0", "GTVp", "PTV", "CTV_0", "CTV_1", "CTV_2"]),  # <-- "ptv x" excluded, ordered by our match list
                ("extra", ["ExtraROI", "ExtraROI2"])
            ]
        ),
        (
            ROI_HANDLING.KEEP_FIRST,
            [
                ("GTV", "GTV 0"),
                ("PTV", "PTV"),  # <-- "ptv x" not considered
                ("TV", "GTV 0"),  # First match among CTV/GTV/PTV
                ("extra", "ExtraROI")
            ]
        )
    ]
)
def test_handle_roi_matching_strategies(roi_names, roi_matching, strategy, expected_output):
    roi_names = sorted(roi_names)
    print(f"roi_names: {roi_names}")
    results = handle_roi_matching(
        roi_names=roi_names,
        roi_matching=roi_matching,
        strategy=strategy,
        ignore_case=False,
    )

    if strategy == ROI_HANDLING.MERGE:
        # Group results by key and assert set equality
        for match in results:
            expected = next((exp for exp in expected_output if exp[0] == match.key), None)
            assert expected is not None, f"Unexpected group {match.key}"
            assert match.matches == expected[1]
    else:
        actual_pairs = [
            (f"{res.key}", res.matches[0])
            for res in results
        ]
        assert actual_pairs == expected_output