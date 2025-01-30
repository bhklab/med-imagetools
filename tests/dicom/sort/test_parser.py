import re
import warnings

import pytest

from imgtools.dicom.sort.exceptions import InvalidPatternError
from imgtools.pattern_parser.parser import PatternParser

# Disable warnings for the purpose of this test
warnings.filterwarnings('ignore', category=pytest.PytestWarning)

# Define a mapping of pattern parsers to their valid test cases
# The second element of tuple is a list of test cases, each containing:
# - A pattern string
# - The expected formatted pattern
# - A list of expected keys
pattern_parsers_and_patterns = [
    # Default pattern parser
    (
        re.compile(r'%<(\w+)>|\{(\w+)\}'),
        [
            ('%<Key1> and {Key2}', '%(Key1)s and %(Key2)s', ['Key1', 'Key2']),
            ('%<Key1>-%<Key2>', '%(Key1)s-%(Key2)s', ['Key1', 'Key2']),
            ('{Key1}_{Key2}', '%(Key1)s_%(Key2)s', ['Key1', 'Key2']),
            ('{Key1} and some text', '%(Key1)s and some text', ['Key1']),
        ],
    ),
    # Alternative placeholder parser
    (
        re.compile(r'<(\w+)>|\[(\w+)\]'),
        [
            ('<Key1> and [Key2]', '%(Key1)s and %(Key2)s', ['Key1', 'Key2']),
            ('<Key1>-<Key2>', '%(Key1)s-%(Key2)s', ['Key1', 'Key2']),
            ('[Key1]_[Key2]', '%(Key1)s_%(Key2)s', ['Key1', 'Key2']),
            ('<Key1> and plain text', '%(Key1)s and plain text', ['Key1']),
        ],
    ),
    # Custom placeholder parser
    (
        re.compile(r'#(\w+)!|\$<(\w+)>'),
        [
            ('#Key1! and $<Key2>', '%(Key1)s and %(Key2)s', ['Key1', 'Key2']),
            ('#Key1!-$<Key2>', '%(Key1)s-%(Key2)s', ['Key1', 'Key2']),
            ('$<Key1>_#Key2!', '%(Key1)s_%(Key2)s', ['Key1', 'Key2']),
            ('$<Key1> and filler text', '%(Key1)s and filler text', ['Key1']),
        ],
    ),
    # Additional pattern example, no numbers involved in keys
    (
        re.compile(r'%([A-Za-z]+)|\{([A-Za-z]+)\}'),
        [
            ('%Key and {Keytwo}', '%(Key)s and %(Keytwo)s', ['Key', 'Keytwo']),
            ('%Key1 and {Keytwo}', '%(Key)s1 and %(Keytwo)s', ['Key', 'Keytwo']),
            ('%Key1-%Keytwo2', '%(Key)s1-%(Keytwo)s2', ['Key', 'Keytwo']),
            ('{Key}_{KeyTWO}', '%(Key)s_%(KeyTWO)s', ['Key', 'KeyTWO']),
            ('{Key} and some text', '%(Key)s and some text', ['Key']),
        ],
    ),
]


class TestPatternParser:
    @pytest.mark.parametrize('pattern_parser, test_cases', pattern_parsers_and_patterns)
    def test_valid_patterns(self, pattern_parser, test_cases) -> None:
        for pattern, expected_format, expected_keys in test_cases:
            parser = PatternParser(pattern, pattern_parser)
            formatted_pattern, keys = parser.parse()
            assert formatted_pattern == expected_format
            assert keys == expected_keys
            assert parser.keys == expected_keys

    @pytest.mark.parametrize('pattern_parser, _', pattern_parsers_and_patterns)
    def test_empty_pattern(self, pattern_parser, _) -> None:
        with pytest.raises(AssertionError, match='Pattern must be a non-empty string.'):
            parser = PatternParser('', pattern_parser)
            parser.parse()

    @pytest.mark.parametrize('pattern_parser, _', pattern_parsers_and_patterns)
    def test_invalid_pattern(self, pattern_parser, _) -> None:
        with pytest.raises(InvalidPatternError, match='Pattern must contain placeholders matching'):
            parser = PatternParser('Invalid pattern', pattern_parser)
            parser.parse()

    @pytest.mark.parametrize('pattern_parser, _', pattern_parsers_and_patterns)
    def test_none_pattern(self, pattern_parser, _) -> None:
        with pytest.raises(AssertionError, match='Pattern must be a non-empty string.'):
            parser = PatternParser(None, pattern_parser)
            parser.parse()
