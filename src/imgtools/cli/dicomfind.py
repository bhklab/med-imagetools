import pathlib
import re
from typing import List

import click

from imgtools.dicom.dicom_find import find_dicoms
from imgtools.logging import logger


def natural_sort_key(s: str) -> list:
    """Generate a natural sorting key from a string.
    
    Splits the input string into numeric and non-numeric segments, converting digit groups to
    integers and non-digit parts to lowercase strings to enable natural order sorting.
    """
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r"(\d+)", str(s))
    ]


@click.command()
@click.argument(
    "path",
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
    "search_input",
    nargs=-1,  # Allow multiple search inputs
    type=str,
    required=False,
)
@click.option(
    "-e",
    "--extension",
    default="dcm",
    show_default=True,
    help="File extension to look for.",
)
@click.option(
    "-c",
    "--count",
    is_flag=True,
    default=False,
    show_default=True,
    help="Whether to just print the count of files found. This is useful for scripts.",
)
@click.option(
    "-l",
    "--limit",
    default=None,
    type=int,
    show_default=True,
    help="The limit of results to return.",
)
@click.option(
    "-ch",
    "--check-header",
    is_flag=True,
    default=False,
    show_default=True,
    help='Whether to check DICOM header for "DICM" signature.',
)
@click.option(
    "-s",
    "--sorted",
    "sort_results",
    is_flag=True,
    default=False,
    show_default=True,
    help="Sort the results alphabetically.",
)
@click.help_option(
    "-h",
    "--help",
)
def dicomfind(
    search_input: List[str],
    path: pathlib.Path,
    extension: str,
    check_header: bool,
    count: bool,
    limit: int,
    sort_results: bool,
) -> None:
    """
    Search and display DICOM files matching specified criteria.
    
    This command-line utility searches for DICOM files in the given directory and filters
    them based on file extension, header verification, and optional substring matches.
    If multiple substrings are provided, a file must contain all of them to be selected.
    The function can limit the number of results, sort them in natural order, or display only
    the total count of matching files.
      
    Args:
        search_input: List of substrings that must all appear in a DICOM file.
        path: Directory in which to search for DICOM files.
        extension: File extension used to identify DICOM files (e.g., "dcm").
        check_header: If True, validates that a file's header contains the "DICM" signature.
        count: When True, displays only the number of matching files.
        limit: Maximum number of files to return.
        sort_results: If True, sorts the found files in natural (human-friendly) order.
    """
    logger.info("Searching for DICOM files.", args=locals())

    dicom_files = find_dicoms(
        directory=path,
        check_header=check_header,
        recursive=True,
        extension=extension,
        limit=limit,  # Pass limit parameter
        search_input=search_input,
    )

    if not dicom_files:
        warningmsg = f"No DICOM files found in {path}."
        if not dicom_files:
            warningmsg += f' Search input "{search_input}" did not match any DICOM files.'
            warningmsg += (
                " Note: ALL search inputs must match to return a result."
            )
        logger.warning(
            warningmsg,
            directory=path,
            check_header=check_header,
            recursive=True,
            extension=extension,
            limit=limit,
            search_input=search_input,
        )
        return

    logger.info("DICOM find successful.", count=len(dicom_files))

    if count:
        click.echo(f"Number of DICOM files found: {len(dicom_files)}")
        return

    if sort_results:
        dicom_files = sorted(
            dicom_files, key=lambda p: natural_sort_key(str(p))
        )

    logger.info("Search complete.")

    for dicom_file in dicom_files:
        click.echo(dicom_file)