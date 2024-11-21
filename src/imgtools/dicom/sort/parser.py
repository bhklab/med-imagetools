"""
Parser module for extracting and validating placeholders from target patterns.

Classes
-------
PatternParser
    A class to parse, validate, and sanitize patterns.
"""

from typing import List, Match, Pattern, Tuple

from imgtools.dicom.sort.exceptions import InvalidPatternError


class PatternParser:
	"""
	A helper class to parse, validate, and sanitize sorting patterns.

	This class handles:
	- Pattern parsing and validation
	- Key extraction from patterns

	Parameters
	----------
	pattern : str
	    The pattern string to parse.
	pattern_parser : Pattern, optional
	    Custom regex pattern for parsing

	Attributes
	----------
	keys : list of str
	    Extracted keys from the pattern.
	"""

	def __init__(self, pattern: str, pattern_parser: Pattern) -> None:
		assert isinstance(pattern, str), 'Pattern must be a string.'
		self._pattern = pattern
		self._keys: List[str] = []
		assert isinstance(pattern_parser, Pattern), 'Pattern parser must be a regex pattern.'
		self._parser: Pattern = pattern_parser

	def parse(self) -> Tuple[str, List[str]]:
		"""
		Parse and validate the pattern.

		Returns
		-------
		Tuple[str, List[str]]
		    The formatted pattern string and a list of extracted keys.

		Raises
		------
		InvalidPatternError
		    If the pattern contains no valid placeholders or is invalid.
		"""
		if not self._pattern or not self._pattern.strip():
			errmsg = 'Pattern cannot be empty or None.'
			raise InvalidPatternError(errmsg)

		sanitized_pattern = self._pattern.strip()
		if not self._parser.search(sanitized_pattern):
			errmsg = "Pattern must contain placeholders matching '%<Key>' or '{Key}'."
			raise InvalidPatternError(errmsg)

		formatted_pattern = self._parser.sub(self._replace_key, sanitized_pattern)
		return formatted_pattern, self._keys

	def _replace_key(self, match: Match) -> str:
		"""Replace placeholders with formatted keys and store them."""
		key = match.group(1) or match.group(2)
		self._keys.append(key)
		return f'%({key})s'

	@property
	def keys(self) -> List[str]:
		"""Get the list of extracted keys."""
		return self._keys
