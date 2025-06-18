from imgtools.coretypes.masktypes import (
    ROIMatcher,
    ROIMatchStrategy,
    handle_roi_matching,
    ROIMatchFailurePolicy,
)
import pytest
from rich import print

# mark this module as 'unittests'
pytestmark = pytest.mark.unittests

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


def test_multi_key_matches(roi_names, roi_matching):
    """Test the allow_multi_key_matches parameter."""
    roi_names = ["GTVp", "CTV_1"]
    roi_matching = {
        "gtv": ["GTV.*"],
        "tumor": ["GTVp.*"],
        "clinical": ["CTV.*"],
    }
    
    # Test with allow_multi_key_matches=True (default)
    results = handle_roi_matching(
        roi_names=roi_names,
        roi_matching=roi_matching,
        strategy=ROIMatchStrategy.MERGE,
        ignore_case=True,
        allow_multi_key_matches=True,
    )
    result_dict = dict(results)
    
    # GTVp should match both "gtv" and "tumor" keys
    assert "gtv" in result_dict
    assert "tumor" in result_dict
    assert "GTVp" in result_dict["gtv"]
    assert "GTVp" in result_dict["tumor"]
    
    # Test with allow_multi_key_matches=False
    results = handle_roi_matching(
        roi_names=roi_names,
        roi_matching=roi_matching,
        strategy=ROIMatchStrategy.MERGE,
        ignore_case=True,
        allow_multi_key_matches=False,
    )
    result_dict = dict(results)
    
    # GTVp should only match the first key "gtv" since allow_multi_key_matches=False
    assert "gtv" in result_dict
    assert "GTVp" in result_dict["gtv"]
    
    # It should not match "tumor" even though the pattern would match
    if "tumor" in result_dict:
        assert "GTVp" not in result_dict["tumor"]

# This has now been moved to the RTStructureset and SEG class to_vector_mask methods
# def test_missing_regex_policy(roi_names, caplog):
#     """Test the on_missing_regex parameter."""
#     # No ROIs that would match these patterns
#     roi_names = ["JUNK1", "JUNK2"]
#     roi_matching = {
#         "gtv": ["GTV.*"],
#         "ptv": ["PTV.*"],
#     }
    
#     # Test with IGNORE policy
#     results = handle_roi_matching(
#         roi_names=roi_names,
#         roi_matching=roi_matching,
#         strategy=ROIMatchStrategy.MERGE,
#         on_missing_regex=ROIMatchFailurePolicy.IGNORE,
#     )
#     assert len(results) == 0  # No matches

#     # need to propagate the logger to capture the logs
#     imgtools_logger = logging.getLogger("imgtools")
#     imgtools_logger.setLevel(logging.DEBUG)
#     imgtools_logger.propagate = True
#     # Test with WARN policy
#     with caplog.at_level(logging.WARNING):
#         results = handle_roi_matching(
#             roi_names=roi_names,
#             roi_matching=roi_matching,
#             strategy=ROIMatchStrategy.MERGE,
#             on_missing_regex=ROIMatchFailurePolicy.WARN,
#         )
#         assert len(results) == 0  # No matches
#         # Check that a warning was logged
#         assert "No ROIs matched any patterns" in caplog.text
    
#     # Test with ERROR policy
#     with pytest.raises(ValueError, match="No ROIs matched any patterns"):
#         handle_roi_matching(
#             roi_names=roi_names,
#             roi_matching=roi_matching,
#             strategy=ROIMatchStrategy.MERGE,
#             on_missing_regex=ROIMatchFailurePolicy.ERROR,
#         )


def test_roi_matcher_class_with_new_params():
    """Test the ROIMatcher class with the new parameters."""
    matcher = ROIMatcher(
        match_map={"gtv": ["GTV.*"], "tumor": ["GTVp.*"]},
        allow_multi_key_matches=False,
        on_missing_regex=ROIMatchFailurePolicy.ERROR,
    )
    
    assert matcher.allow_multi_key_matches is False
    assert matcher.on_missing_regex == ROIMatchFailurePolicy.ERROR
    
    # Test that the parameters are passed correctly to handle_roi_matching
    # when calling match_rois (we can't easily test this directly, so we'll
    # use a test case where we know the behavior differs)
    # This should not raise an error even with on_missing_regex=ERROR
    # because there are matches
    results = matcher.match_rois(["GTVp"])
    result_dict = dict(results)
    
    # GTVp should only match "gtv" since allow_multi_key_matches=False
    assert "gtv" in result_dict
    assert "GTVp" in result_dict["gtv"]
    
    # It should not be in "tumor" even though the pattern matches
    if "tumor" in result_dict:
        assert "GTVp" not in result_dict["tumor"]
    


def test_keep_first_with_no_multi_key_matches():
    """Test the interaction between KEEP_FIRST and allow_multi_key_matches=False.
    
    This test addresses the edge case where an ROI could be missed entirely
    if it was the second match for the first key, but could have been the
    first match for the second key.
    """
    # These ROIs demonstrate the potential issue
    roi_names = ["GTVp", "GTVp_2", "CTV"]
    
    # In this matching setup:
    # - GTVp matches both "gtv" and "tumor" 
    # - GTV_primary only matches "gtv"
    # - CTV only matches "clinical"
    roi_matching = {
        "gtv": ["GTV.*"],      # Matches both "GTVp" and "GTV_primary"
        "tumor": ["GTVp.*"],   # Only matches "GTVp"
        "clinical": ["CTV.*"], # Only matches "CTV"
    }
    
    # With allow_multi_key_matches=True, GTVp could match both keys
    results = handle_roi_matching(
        roi_names=roi_names,
        roi_matching=roi_matching,
        strategy=ROIMatchStrategy.KEEP_FIRST,
        ignore_case=True,
        allow_multi_key_matches=True,
    )
    result_dict = dict(results)
        # GTVp should be the match for "gtv" (first ROI matching the pattern)
    assert "gtv" in result_dict
    assert result_dict["gtv"] == ["GTVp"]
    
    # GTVp should also be the match for "tumor"
    assert "tumor" in result_dict
    assert result_dict["tumor"] == ["GTVp"]
    
    # And CTV should match "clinical"
    assert "clinical" in result_dict
    assert result_dict["clinical"] == ["CTV"]
    
    # With allow_multi_key_matches=False and the FIXED implementation:
    results = handle_roi_matching(
        roi_names=roi_names,
        roi_matching=roi_matching,
        strategy=ROIMatchStrategy.KEEP_FIRST,
        ignore_case=True,
        allow_multi_key_matches=False,
    )
    result_dict = dict(results)
    
    # We should have optimal assignment:
    # - "gtv" should get GTV_primary (since GTVp is better used elsewhere)
    # - "tumor" should get GTVp (since it can ONLY match GTVp)
    # - "clinical" should get CTV
    
    # This ensures we don't miss any ROIs that could have been matched
    assert "gtv" in result_dict
    assert result_dict["gtv"] == ["GTVp"]
    
    assert "tumor" in result_dict
    assert result_dict["tumor"] == ["GTVp_2"]
    
    assert "clinical" in result_dict
    assert result_dict["clinical"] == ["CTV"]
