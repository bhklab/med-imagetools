from imgtools.coretypes.masktypes import (
    ROIMatcher,
    ROI_HANDLING,
    handle_roi_matching,
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
        "PTV main", "ptv x",
        "", "UNKNOWN_ROI", "gtv 0", "extraROI"
    ]
    return rois


@pytest.fixture
def roi_matching():
    return {
        "GTV": ["GTV.*"],
        "PTV": ["PTV.*"],
        "TV": ["GTV.*", "PTV.*", "CTV.*"],
        "extra": ["Extra.*"],
    }


@pytest.mark.parametrize(
    "strategy,expected_output,expected_output_ignorecase",
    [
        (   # strategy
            ROI_HANDLING.SEPARATE,
            # expected output case sensitive
            [
                ("GTV", "GTV 0"), ("GTV", "GTVp"),
                ("PTV", "PTV main"), # 'ptv x' is not included in the expected output 
                ("TV", "GTV 0"), ("TV", "GTVp"), ("TV", "PTV main"), ("TV", "CTV_0"), ("TV", "CTV_1"), ("TV", "CTV_2"),
                ("extra", "ExtraROI"), ("extra", "ExtraROI2")
            ],
            # expected output case insensitive
            [
                ("GTV", "GTV 0"), ("GTV", "GTVp"), ("GTV", "gtv 0"),
                ("PTV", "PTV"), ("PTV", "ptv x"),
                ("TV", "GTV 0"), ("TV", "GTVp"), ("TV", "gtv 0"), ("TV", "PTV"), ("TV", "ptv x"), ("TV", "CTV_0"), ("TV", "CTV_1"), ("TV", "CTV_2"),
                ("extra", "ExtraROI"), ("extra", "ExtraROI2"), ("extra", "extraROI")
            ]
        ),
        (   # strategy
            ROI_HANDLING.MERGE,
            # expected output case sensitive
            [
                ("GTV", ["GTV 0", "GTVp"]),
                ("PTV", ["PTV main"]),
                ("TV", ["GTV 0", "GTVp", "PTV main", "CTV_0", "CTV_1", "CTV_2"]),
                ("extra", ["ExtraROI", "ExtraROI2"])
            ],
            # expected output case insensitive
            [
                ("GTV", ["GTV 0", "GTVp", "gtv 0"]),
                ("PTV", ["PTV main", "ptv x"]),
                ("TV", ["GTV 0", "GTVp", "gtv 0", "PTV main", "ptv x", "CTV_0", "CTV_1", "CTV_2"]),
                ("extra", ["ExtraROI", "ExtraROI2", "extraROI"])
            ]
        ),
        (   # strategy
            ROI_HANDLING.KEEP_FIRST,
            # expected output case sensitive
            [
                ("GTV", "GTV 0"),
                ("PTV", "PTV main"),
                ("TV", "GTV 0"),
                ("extra", "ExtraROI")
            ],
            # expected output case insensitive
            [
                ("GTV", "GTV 0"),
                ("PTV", "PTV main"),
                ("TV", "GTV 0"),
                ("extra", "ExtraROI")
            ]
        )
    ]
)
def test_handle_roi_matching_strategies(
    roi_names,
    roi_matching,
    strategy,
    expected_output,
    expected_output_ignorecase
):
    roi_names = sorted(roi_names)

    # Case-sensitive matching
    results_case_sens = handle_roi_matching(
        roi_names=roi_names,
        roi_matching=roi_matching,
        strategy=strategy,
        ignore_case=False,
    )

    if strategy == ROI_HANDLING.MERGE:
        for key, expected_matches in expected_output:
            assert key in results_case_sens 
            assert results_case_sens[key] == expected_matches
    elif strategy == ROI_HANDLING.KEEP_FIRST:
        actual_pairs = [(key, values[0]) for key, values in results_case_sens.items()]
        assert sorted(actual_pairs) == sorted(expected_output)
    elif strategy == ROI_HANDLING.SEPARATE:
        actual_pairs = []
        for key, values in results_case_sens.items():
            actual_pairs.extend([(key, value) for value in values])

        assert sorted(actual_pairs) == sorted(expected_output)

    # Case-insensitive matching
    results_case_insens = handle_roi_matching(
        roi_names=roi_names,
        roi_matching=roi_matching,
        strategy=strategy,
        ignore_case=True,
    )

    if strategy == ROI_HANDLING.MERGE:
        for key, expected_matches in expected_output_ignorecase:
            assert key in results_case_insens 
            assert results_case_insens[key] == expected_matches
    elif strategy == ROI_HANDLING.KEEP_FIRST:
        actual_pairs = [(key, values[0]) for key, values in results_case_insens.items()]
        assert sorted(actual_pairs) == sorted(expected_output_ignorecase)
    elif strategy == ROI_HANDLING.SEPARATE:
        actual_pairs = []
        for key, values in results_case_insens.items():
            actual_pairs.extend([(key, value) for value in values])
