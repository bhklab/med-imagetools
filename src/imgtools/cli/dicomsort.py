import pathlib

import click

from imgtools.dicom.sort import DICOMSorter, FileAction
from imgtools.logging import logger


@click.command()
@click.argument(
	'source_directory',
	type=click.Path(
		exists=True,
		file_okay=False,
		dir_okay=True,
		readable=True,
		path_type=pathlib.Path,
		resolve_path=True,
	),
)
@click.argument(
	'target_directory',
	type=click.Path(
		file_okay=False,
		writable=True,
		path_type=str,  # TODO: figure out if patterned path i.e data/%PatientID can be a pathlib.Path
	),
)
@click.option(
	'--action',
	'-a',
	type=click.Choice(FileAction.choices(), case_sensitive=False),
	required=True,
	help='Action to perform on the files.',
)
@click.option(
	'-n',
	'--dry-run',
	is_flag=True,
	help='Do not move or copy files, just print what would be done. Always recommended to use this first to confirm the operation!',
)
@click.option(
	'-o',
	'--overwrite',
	is_flag=True,
	default=False,
	show_default=True,
	help='Force overwrite any files that already exist in the target directory. '
	'NOT RECOMMENDED! if two files from source resolve to the same target path, data loss may occur.',
)
@click.option(
	'-j',
	'--num-workers',
	type=int,
	default=1,
	show_default=True,
	help='Number of worker processes to use for sorting.',
)
@click.help_option(
	'-h',
	'--help',
)
def dicomsort(
	source_directory: pathlib.Path,
	target_directory: str,
	action: FileAction,
	dry_run: bool,
	overwrite: bool,
	num_workers: int,
) -> None:
	"""Sorts DICOM files into directories based on their tags."""
	logger.info(f'Sorting DICOM files in {source_directory}.')
	logger.debug('Debug Args', args=locals())
	# TODO: eagerly validate target pattern somehow?

	try:
		sorter = DICOMSorter(
			source_directory=source_directory,
			target_pattern=target_directory,
		)
	except Exception as e:
		logger.exception('Failed to initialize DICOMSorter')
		raise click.Abort() from e

	sorter.execute(
		action=action,
		overwrite=overwrite,
		dry_run=dry_run,
		num_workers=num_workers,
	)


if __name__ == '__main__':
	dicomsort()
