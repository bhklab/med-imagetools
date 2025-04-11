from imgtools.coretypes.masktypes import (
    ROIMatcher,
    ROIMatchStrategy,
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
    roimatcher = ROIMatcher(match_map=roi_matching)
    result = roimatcher.match_map
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
            ROIMatchStrategy.SEPARATE,
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
                ("PTV", "PTV main"), ("PTV", "ptv x"),
                ("TV", "GTV 0"), ("TV", "GTVp"), ("TV", "gtv 0"), ("TV", "PTV main"), ("TV", "ptv x"), ("TV", "CTV_0"), ("TV", "CTV_1"), ("TV", "CTV_2"),
                ("extra", "ExtraROI"), ("extra", "ExtraROI2"), ("extra", "extraROI")
            ]
        ),
        (   # strategy
            ROIMatchStrategy.MERGE,
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
            ROIMatchStrategy.KEEP_FIRST,
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

    # Test case-sensitive matching
    results = handle_roi_matching(
        roi_names=roi_names,
        roi_matching=roi_matching,
        strategy=strategy,
        ignore_case=False,
    )

    expected = expected_output
    if strategy == ROIMatchStrategy.MERGE:
        result_dict = dict(results)
        for key, expected_matches in expected:
            assert key in result_dict
            assert result_dict[key] == expected_matches

    elif strategy == ROIMatchStrategy.KEEP_FIRST:
        actual_pairs = [(key, values[0]) for key, values in results]
        assert sorted(actual_pairs) == sorted(expected)

    elif strategy == ROIMatchStrategy.SEPARATE:
        actual_pairs = [(key, values[0]) for key, values in results]
        assert sorted(actual_pairs) == sorted(expected)

    # Test case-insensitive matching
    results = handle_roi_matching(
        roi_names=roi_names,
        roi_matching=roi_matching,
        strategy=strategy,
        ignore_case=True,
    )

    expected = expected_output_ignorecase
    if strategy == ROIMatchStrategy.MERGE:
        result_dict = dict(results)
        for key, expected_matches in expected:
            assert key in result_dict
            assert result_dict[key] == expected_matches

    elif strategy == ROIMatchStrategy.KEEP_FIRST:
        actual_pairs = [(key, values[0]) for key, values in results]
        assert sorted(actual_pairs) == sorted(expected)

    elif strategy == ROIMatchStrategy.SEPARATE:
        actual_pairs = [(key, values[0]) for key, values in results]
        assert sorted(actual_pairs) == sorted(expected)
