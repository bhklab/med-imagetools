"""
Sorting DICOM files by specific tags and patterns.

This module provides tools to sort DICOM files into structured
directories based on customizable target patterns. The target
patterns define directory structures using placeholders for DICOM
tags, allowing for metadata-driven file organization.

**Important**:
The filename (basename) of each source file remains unchanged
during the sorting process. Only the directory structure is
modified to match the resolved metadata fields from the target
pattern. This design ensures that files with identical metadata
fields do not overwrite one another, preserving their unique
identifiers within the new directory.

Examples
--------
Source file:
`/source_dir/HN-CHUS-082/1-1.dcm`

Target pattern:
`./data/dicoms/%PatientID/Study-%StudyInstanceUID/Series-%SeriesInstanceUID/%Modality/`

Resolved path:
`./data/dicoms/HN-CHUS-082/Study-06980/Series-67882/RTSTRUCT/1-1.dcm`

Here, the file is relocated into the resolved directory structure,
but the basename `1-1.dcm` remains intact

Target patterns support placeholders for DICOM tags:
`%PatientID/%StudyID/{SeriesID}/`
`path/to_destination-Directory/%PatientID/images/dicoms/%Modality/%SeriesInstanceUID/`

Placeholders support `%<DICOMKey>` and `{DICOMKey}` syntax.


Classes
-------
DICOMSorter
    A concrete implementation of `SorterBase` for organizing DICOM
    files by metadata-driven patterns.
"""

import contextlib
import re
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Pattern, Set

from rich import progress
from rich.console import Console
from rich.theme import Theme

from imgtools.dicom import similar_tags, tag_exists
from imgtools.dicom.sort import (
	DicomKeyHighlighter,
	FileAction,
	InvalidDICOMKeyError,
	SorterBase,
	handle_file,
	resolve_path,
)

DEFAULT_PATTERN_PARSER: Pattern = re.compile(r'%([A-Za-z]+)|\{([A-Za-z]+)\}')


class DICOMSorter(SorterBase):
	"""A specialized implementation of the `SorterBase` for sorting DICOM files by metadata.

	This class resolves paths for DICOM files based on specified
	target patterns, using metadata extracted from the files. The
	filename of each source file is preserved during this process.

	Attributes
	----------
	source_dirctory : Path
	    The directory containing the files to be sorted.
	logger : Logger
	    The instance logger bound with the source directory context.
	dicom_files : list of Path
	    The list of DICOM files found in the `source_directory`.
	format : str
	    The parsed format string with placeholders for DICOM tags.
	keys : Set[str] 
	    DICOM tags extracted from the target pattern.
	invalid_keys : Set[str] 
	    DICOM tags from the pattern that are invalid.
	format : str
	    The parsed format string with placeholders for keys.
	console : Console
	    Rich console object for highlighting and printing.
	"""

	def __init__(
		self,
		source_dirctory: Path,
		target_pattern: str,
		pattern_parser: Pattern = DEFAULT_PATTERN_PARSER,
	) -> None:
		super().__init__(
			source_dirctory=source_dirctory,
			target_pattern=target_pattern,
			pattern_parser=pattern_parser,
		)
		self.logger.debug('All DICOM Keys are Valid in target pattern', keys=self.keys)

	def validate_keys(self) -> None:
		"""Validate the DICOM keys in the target pattern.

		If any invalid keys are found, it
		suggests similar valid keys and raises an error.
		"""
		if not self.invalid_keys:
			return

		for key in sorted(self.invalid_keys):
			# TODO: keep this logic, but make the suggestion more user-friendly/readable
			similar = similar_tags(key)
			suggestion = (
				f"\n\tDid you mean: [bold green]{', '.join(similar)}[/bold green]?"
				if similar
				else ' And [bold red]no similar keys[/bold red] found.'
			)
			_error = f'Invalid DICOM key: [bold red]{key}[/bold red].{suggestion}'
			self._console.print(f'{_error}')
		self.console.print(f'Parsed Path: `{self.pattern_preview}`')
		errmsg = 'Invalid DICOM Keys found.'
		raise InvalidDICOMKeyError(errmsg)

	def _initialize_console(self) -> Console:
		return Console(
			highlighter=DicomKeyHighlighter(),
			theme=Theme(
				{
					'example.DicomTag': 'bold magenta',
					'example.ForwardSlash': 'bold green',
					'example.Braces': 'bold magenta',
				}
			),
		)

	@property
	def invalid_keys(self) -> Set[str]:
		"""Get the set of invalid keys.

		Essentially, this will check `pydicom.dictionary_has_tag` for each key
		in the pattern and return the set of keys that are invalid.

		Returns
		-------
		Set[str]
		    The set of invalid keys.
		"""
		return {key for key in self.keys if not tag_exists(key)}

	def execute(
		self,
		action: FileAction = FileAction.MOVE,
		overwrite: bool = False,
		dry_run: bool = False,
		num_workers: int = 1,
	) -> None:
		"""Execute the file action on DICOM files.

		Users are encouraged to use FileAction.HARDLINK for 
		efficient storage and performance for large dataset, as well as
		protection against lost data. 

		Using hard links can save disk space and improve performance by
		creating multiple directory entries (links) for a single file
		instead of duplicating the file content. This is particularly
		useful when working with large datasets, such as DICOM files,
		where storage efficiency is crucial.

		Parameters
		----------
		action : FileAction, default: FileAction.MOVE
			The action to apply to the DICOM files (e.g., move, copy).
		overwrite : bool, default: False
			If True, overwrite existing files at the destination.
		dry_run : bool, default: False
			If True, perform a dry run without making any changes.
		num_workers : int, default: 1
			The number of worker threads to use for processing files.

		Raises
		------
		ValueError
			If the provided action is not a valid FileAction.
		"""
		if not isinstance(action, FileAction):
			try:
				action = FileAction(action)
			except ValueError as e:
				valid_actions = ', '.join([f'`{a.value}`' for a in FileAction])
				msg = f'Invalid action: {action}. Must be one of: {valid_actions}'
				raise ValueError(msg) from e

		self.logger.debug(f'Mapping {len(self.dicom_files)} files to new paths')

		# Create a progress bar that can be used to track eveerything
		with progress.Progress(
			'[progress.description]{task.description}',
			progress.BarColumn(),
			'[progress.percentage]{task.percentage:>3.0f}%',
			progress.MofNCompleteColumn(),
			'Time elapsed:',
			progress.TimeElapsedColumn(),
			console=self.console,
			transient=True,
		) as progress_bar:
			################################################################################
			# Resolve new paths
			################################################################################
			file_map: Dict[Path, Path] = self._resolve_new_paths(
				progress_bar=progress_bar, num_workers=num_workers
			)
			self.console.print('Finished resolving paths')
			################################################################################
			# Check if any of the resolved paths are duplicates
			################################################################################
			file_map = self._check_duplicates(file_map)
			self.console.print('Finished checking for duplicates')

			################################################################################
			# Handle files
			################################################################################

			if dry_run:
				print(file_map)
			else:
				task_files = progress_bar.add_task('Handling files', total=len(file_map))
				new_paths = []
				with ProcessPoolExecutor(max_workers=num_workers) as executor:
					future_to_file = {
						executor.submit(
							handle_file, source_path, resolved_path, action, overwrite
						): source_path
						for source_path, resolved_path in file_map.items()
					}
					for future in as_completed(future_to_file):
						result = future.result()
						new_paths.append(result)
						progress_bar.update(task_files, advance=1)

	def _check_duplicates(self, file_map: Dict[Path, Path]) -> Dict[Path, Path]:
		"""
		Check if any of the resolved paths are duplicates.

		Parameters
		----------
		file_map : Dict[Path, Path]
		    A dictionary mapping source paths to resolved paths.

		Returns
		-------
		Dict[Path, Path]
		    A dictionary mapping source paths to resolved paths.

		Raises
		------
		ValueError
		    If any of the resolved paths are duplicates.
		"""
		# opposite of the file_map
		# key: resolved path, value: list of source paths
		duplicate_paths: Dict[Path, List[Path]] = {}

		for source_path, resolved_path in file_map.items():
			if resolved_path in duplicate_paths:
				duplicate_paths[resolved_path].append(source_path)
			else:
				duplicate_paths[resolved_path] = [source_path]

		duplicates = False
		for resolved_path, source_paths in duplicate_paths.items():
			if len(source_paths) > 1:
				msg = f'Duplicate paths found for {resolved_path}: {source_paths}'
				self.logger.warning(msg)
				duplicates = True

		if duplicates:
			msg = 'Duplicate paths found. Please check the log file for more information.'
			raise ValueError(msg)

		return file_map

	def _resolve_new_paths(
		self, progress_bar: progress.Progress, num_workers: int = 1
	) -> Dict[Path, Path]:
		"""Resolve the new paths for all DICOM files using parallel processing.

		Parameters
		----------
		progress_bar : progress.Progress
			Progress bar to use for tracking the progress of the operation.
		num_workers : int, default=1
			Number of threads to use for parallel processing.

		Returns
		-------
		Dict[Path, Path]
			A mapping of source paths to resolved paths.
		"""
		task = progress_bar.add_task('Resolving paths', total=len(self.dicom_files))

		# Use ProcessPoolExecutor for parallel processing
		results: Dict[Path, Path] = {}
		with ProcessPoolExecutor(max_workers=num_workers) as executor:
			future_to_path = {
				executor.submit(resolve_path, path, self.keys, self.format): path
				for path in self.dicom_files
			}
			for future in as_completed(future_to_path):
				source, resolved = future.result()
				results[source] = resolved
				progress_bar.update(task, advance=1)

		return results


if __name__ == '__main__':
	import time

	from rich import print

	print('Using incorrect pattern:')
	input_dir = Path('data/unsorted/unzipped/TCGA-LGG')
	assert input_dir.exists() and input_dir.is_dir()
	# shutil.rmtree(Path('./data/dicoms/sorted'))
	print('\n\nUsing another correct pattern:')
	correct_pattern = './data/dicoms/sorted/images/%PatientID/Study-%StudyInstanceUID/%Modality_Series-%SeriesInstanceUID/'
	sorter = DICOMSorter(input_dir, correct_pattern)
	# This will be useful for dry-run option
	# sorter.print_tree()

	# start = time.time()
	# sorter.execute(FileAction.COPY, overwrite=False)

	# print(f'Time taken: {time.time() - start:.2f} seconds')

	# # Delete the data/dicoms/sorted directory
	# # shutil.rmtree(Path('./data/dicoms/sorted'))

	# start = time.time()
	# sorter.execute(FileAction.COPY, overwrite=False, num_workers=4)

	# print(f'Time taken: {time.time() - start:.2f} seconds')

	# # Delete the data/dicoms/sorted directory
	with contextlib.suppress(Exception):
		shutil.rmtree(Path('./data/dicoms/sorted'))

	start = time.time()
	sorter.execute(FileAction.SYMLINK, overwrite=False, num_workers=10)

	print(f'Time taken: {time.time() - start:.2f} seconds')
