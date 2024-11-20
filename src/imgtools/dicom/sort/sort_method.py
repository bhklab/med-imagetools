"""
File Handling Utility.

This module provides functionality to handle files with different actions
such as moving, copying, creating symbolic links, and creating hard links.

Classes
-------
FileAction(Enum)
    Enum for file actions including MOVE, COPY, SYMLINK, and HARDLINK.

Functions
---------
handle_file(source_path: Path, resolved_path: Path, action: FileAction, overwrite: bool) -> Path
    Perform specified file operations (move, copy, symlink, hardlink) on a file.

Notes
-----
Symlinks vs. Hardlinks:
- **Symlinks (Symbolic Links)**:
    A symbolic link is a shortcut or reference to another file. It creates a new
    file that points to the target file but does not duplicate the file's data.
    If the target file is moved or deleted, the symlink becomes invalid.
    Example: `ln -s target symlink`

- **Hardlinks**:
    A hard link is an additional reference to the same data on the disk. Both the
    original file and the hard link share the same inode, meaning they are
    indistinguishable. Deleting the original file does not affect the hard link,
    and vice versa.
    Example: `ln target hardlink`

Examples
--------
Move a file:
    >>> from pathlib import Path
    >>> handle_file(Path('source.txt'), Path('destination.txt'), action=FileAction.MOVE)

Create a symlink:
    >>> handle_file(Path('source.txt'), Path('symlink.txt'), action=FileAction.SYMLINK)

Copy a file:
    >>> handle_file(Path('source.txt'), Path('copy.txt'), action=FileAction.COPY, overwrite=True)
"""

import shutil
from enum import Enum
from pathlib import Path
from typing import Type


class FileAction(Enum):
	"""
	Enum for file actions.

	Attributes
	----------
	MOVE : str
	    Move the file from source to destination.
	COPY : str
	    Copy the file from source to destination.
	SYMLINK : str
	    Create a symbolic link at the destination pointing to the source.
	HARDLINK : str
	    Create a hard link at the destination pointing to the source.
	"""

	MOVE = 'move'
	COPY = 'copy'
	SYMLINK = 'symlink'
	HARDLINK = 'hardlink'

	@classmethod
	def validate(cls: Type['FileAction'], action: str) -> 'FileAction':
		if not isinstance(action, cls):
			try:
				return cls(action)
			except ValueError as e:
				valid_actions = ', '.join([f'`{a.value}`' for a in cls])
				msg = f'Invalid action: {action}. Must be one of: {valid_actions}'
				raise ValueError(msg) from e
		return action

	@staticmethod
	def choices() -> list[str]:
		"""Return a list of valid file actions."""
		return [action.value for action in FileAction]


def handle_file(  # noqa: PLR0912
	source_path: Path,
	resolved_path: Path,
	action: FileAction = FileAction.MOVE,
	overwrite: bool = False,
) -> Path:
	"""
	Handle file operations such as move, copy, symlink, or hardlink.

	Parameters
	----------
	source_path : Path
	    The source file path.
	resolved_path : Path
	    The destination file path.
	action : FileAction, optional
	    The action to perform on the file (default is MOVE).
	overwrite : bool, optional
	    If True, overwrite the destination file if it exists (default is False).

	Returns
	-------
	Path
	    The resolved path of the destination file.

	Raises
	------
	ValueError
	    If an invalid action is specified.
	FileExistsError
	    If the destination file exists and overwrite is False.
	FileNotFoundError
	    If the source file does not exist.
	RuntimeError
	    If the file operation fails.

	Notes
	-----
	- Symlinks create a shortcut to the original file, while hard links create an
	  additional reference to the same file data.
	- Moving a file changes its location. Copying a file duplicates it.

	Examples
	--------
	Move a file:
	>>> from pathlib import Path
	>>> handle_file(Path('source.txt'), Path('destination.txt'), action=FileAction.MOVE)

	Create a symbolic link:
	>>> handle_file(Path('source.txt'), Path('symlink.txt'), action=FileAction.SYMLINK)

	Copy a file with overwrite:
	>>> handle_file(Path('source.txt'), Path('copy.txt'), action=FileAction.COPY, overwrite=True)
	"""

	# Handle file existence atomically
	if not overwrite:
		try:
			# Open with exclusive creation flag
			resolved_path.open('x').close()
			resolved_path.unlink()  # Remove the temporary file
		except FileExistsError as fee:
			msg = f'Destination exists: {resolved_path}'
			raise FileExistsError(msg) from fee

	# Check if the source exists
	if not source_path.exists():
		msg = f'Source does not exist: {source_path}'
		raise FileNotFoundError(msg)

	# Ensure the parent directory exists
	try:
		resolved_path.parent.mkdir(parents=True, exist_ok=True)
	except PermissionError as e:
		errmsg = f'Failed to create parent directory: {resolved_path.parent}'
		raise PermissionError(errmsg) from e

	# Perform the file operation
	match action:
		case FileAction.MOVE:
			try:
				source_path.rename(resolved_path)
			except OSError as e:
				errmsg = f'Failed to move file: {source_path} to {resolved_path}'
				raise RuntimeError(errmsg) from e
		case FileAction.COPY:
			try:
				shutil.copy2(source_path, resolved_path)  # shutil.copy2 preserves metadata
			except OSError as e:
				errmsg = f'Failed to copy file: {source_path} to {resolved_path}'
				raise RuntimeError(errmsg) from e
		case FileAction.SYMLINK:
			try:
				real_source = source_path.resolve(strict=True)
				if not real_source.is_relative_to(Path.cwd()):
					errmsg = f'Source path {source_path} points outside current directory'
					raise ValueError(errmsg)
			except (FileNotFoundError, RuntimeError) as e:
				errmsg = f'Invalid source path {source_path}: possible symlink loop'
				raise ValueError(errmsg) from e
			resolved_path.symlink_to(source_path, target_is_directory=False)
		case FileAction.HARDLINK:
			try:
				resolved_path.hardlink_to(source_path)
			except OSError as e:
				errmsg = f'Failed to create hard link: {source_path} to {resolved_path}'
				raise RuntimeError(errmsg) from e
		case _:
			msg = f'Invalid action: {action} must be one of {FileAction.__members__}'
			raise ValueError(msg)

	# Verify that the operation succeeded
	if not resolved_path.exists():
		msg = f'Failed to perform file operation: action={action} on source_path={source_path} to resolved_path={resolved_path}'
		raise RuntimeError(msg)

	return resolved_path


if __name__ == '__main__':
	import time

	start = time.time()
	source_path = Path('./data/hi.txt')
	assert source_path.exists() and source_path.is_file()
	resolved_path = Path('./data/hi-renamed.txt')
	handle_file(
		source_path=source_path,
		resolved_path=resolved_path,
		action=FileAction.COPY,
		overwrite=False,
	)
