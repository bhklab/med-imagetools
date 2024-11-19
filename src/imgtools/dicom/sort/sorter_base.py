"""
Base module for sorting files based on customizable patterns.

This module provides a foundation for implementing file sorting
logic, particularly for handling DICOM files or other structured data.

The `SorterBase` class serves as an abstract base class for:
- Parsing and validating patterns used for organizing files.
- Visualizing the target directory structure through a tree representation.
- Allowing subclasses to implement specific validation and resolution logic.

**Important**:
While this module helps define the target directory structure for
files based on customizable metadata-driven patterns, it **does not
alter the filename (basename)** of the source files. The original
filename is preserved during the sorting process. This ensures that
files with the same metadata fields but different filenames are not
overwritten, which is critical when dealing with fields like
`InstanceNumber` that may have common values across different files.

Examples
--------
Given a source file:
`/source_dir/HN-CHUS-082/1-1.dcm`

And a target pattern:
`./data/dicoms/%PatientID/Study-%StudyInstanceUID/Series-%SeriesInstanceUID/%Modality/`

The resolved path will be:
`./data/dicoms/HN-CHUS-082/Study-06980/Series-67882/RTSTRUCT/1-1.dcm`

The `SorterBase` class ensures that only the directory structure is
adjusted based on metadata, leaving the original filename intact.
"""

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Pattern, Set, Tuple

from rich import progress
from rich.console import Console
from rich.text import Text
from rich.tree import Tree

from imgtools.dicom import find_dicoms
from imgtools.dicom.sort import PatternParser, SorterBaseError
from imgtools.dicom.sort.utils import read_tags
from imgtools.logging import logger

DEFAULT_PATTERN_PARSER: Pattern = re.compile(r'%([A-Za-z]+)|\{([A-Za-z]+)\}')


def worker(path: Path, keys: Set[str], format_str: str) -> Tuple[Path, Path]:
	"""
	Worker function to resolve a single path.

	Parameters
	----------
	path : Path
	    The source file path.
	keys : Set[str]
	    The DICOM keys required for resolving the path.
	format_str : str
	    The format string for the resolved path.

	Returns
	-------
	Tuple[Path, Path]
	    The source path and resolved path.
	"""
	tags: Dict[str, str] = read_tags(path, list(keys), truncate=True, sanitize=True)
	resolved_path = Path(format_str % tags, path.name).resolve()
	return path, resolved_path


class SorterBase(ABC):
	"""
	Abstract base class for sorting files based on customizable patterns.

	This class provides functionalities for:
	- Pattern parsing and validation
	- Tree visualization of file structures
	- Extensibility for subclass-specific implementations

	Parameters
	----------
	source_dirctory : Path
	    The directory containing the files to be sorted.
	target_pattern : str
	    The pattern string for sorting files.
	parse_pattern : Pattern, optional
	    Custom regex pattern for parsing patterns uses default that
			matches placeholders in the format of `%KEY` or `{KEY}`:
	    `re.compile(r"%([A-Za-z]+)|\\{([A-Za-z]+)\\}")`.

	Attributes
	----------
	source_dirctory : Path
	    The directory containing the files to be sorted.
	format : str
	    The parsed format string with placeholders for keys.
	keys : set of str
	    Keys extracted from the target pattern.
	console : Console
	    Rich console object for highlighting and printing.
	logger : Logger
	    The instance logger bound with the source directory context.
	dicom_files : list of Path
	    The list of DICOM files to be sorted.
	"""

	def __init__(
		self,
		source_dirctory: Path,
		target_pattern: str,
		pattern_parser: Pattern = DEFAULT_PATTERN_PARSER,
	) -> None:
		self.source_dirctory = source_dirctory
		self._target_pattern = target_pattern
		self._keys: Set[str] = set()
		self._console: Console = self._initialize_console()
		self.logger = logger.bind(source_dirctory=self.source_dirctory)

		try:
			self.dicom_files = find_dicoms(
				directory=self.source_dirctory,
				check_header=False,
				recursive=True,
				extension='dcm',
			)
			self.logger.info(f'Found {len(self.dicom_files)} files')
		except Exception as e:
			errmsg = 'Failed to find files in the source directory.'
			raise SorterBaseError(errmsg) from e

		try:
			self._parser = PatternParser(target_pattern, pattern_parser)
			self._format, parsed_keys = self._parser.parse()
			self._keys = set(parsed_keys)
		except Exception as e:
			errmsg = 'Failed to initialize SorterBase.'
			raise SorterBaseError(errmsg) from e
		self.validate_keys()

	@abstractmethod
	def _initialize_console(self) -> Console:
		"""Initialize a rich console with optional highlighting."""
		pass

	@abstractmethod
	def validate_keys(self) -> None:
		"""
		Validate extracted keys. Subclasses should implement this method
		to perform specific validations based on their context.
		"""
		pass

	@abstractmethod
	def resolve_new_paths(
		self, progress_bar: progress.Progress, num_workers: int = 1
	) -> Dict[Path, Path]:
		"""Resolve the new path based on the extracted keys.

		Returns
		-------
		Dict[Path]
				A list of resolved paths, each preserving the original filename.
		"""
		pass

	def _generate_tree_structure(self, path: str, tree: Tree) -> None:
		"""Generate a tree structure from the pattern path."""
		if not path:
			return
		parts = path.split('/')
		if parts[0] in ['', '.', '/']:
			parts = parts[1:]
		style = 'dim' if parts[0].startswith('__') else ''

		highlighted_label = Text(parts[0], style=style)
		highlighted_label.highlight_regex(r'\{[a-zA-Z0-9_]+\}', 'bold magenta')
		branch = tree.add(highlighted_label, style=style, guide_style=style)
		self._generate_tree_structure('/'.join(parts[1:]), branch)

	def _setup_tree(self, base_dir: Path) -> Tree:
		"""
		Set up the initial tree for visualization.

		Parameters
		----------
		base_dir : Path
		    The base directory for the tree.

		Returns
		-------
		Tree
		    The initialized tree object.
		"""
		tree = Tree(f':file_folder: {base_dir}/', guide_style='bold bright_blue')
		self._generate_tree_structure(self.pattern_preview, tree)
		return tree

	@property
	def pattern_preview(self) -> str:
		"""Returns a human readable preview of the pattern.

		Useful for visualizing the pattern structure and can be
		highlighted using Rich Console.

		Examples
		--------
		>>> target_pattern = '%key1/%key2/%key3'
		>>> pattern_preview = '{key1}/{key2}/{key3}'
		"""
		replacements = {key: f'{{{key}}}' for key in self.keys}
		return self.format % replacements

	@property
	def console(self) -> Console:
		"""Get the rich console object."""
		return self._console

	@property
	def format(self) -> str:
		"""Get the formatted pattern string."""
		return self._format

	@property
	def keys(self) -> Set[str]:
		"""Get the set of keys extracted from the pattern."""
		return self._keys

	def print_tree(self) -> None:
		"""
		Display the pattern structure as a tree visualization.

		Raises
		------
		SorterBaseError
		    If the tree visualization fails to generate.
		"""
		try:
			base_dir = Path().cwd().resolve()
			tree = self._setup_tree(base_dir)
			self._console.print(tree)
		except Exception as e:
			errmsg = 'Failed to generate tree visualization.'
			raise SorterBaseError(errmsg) from e
