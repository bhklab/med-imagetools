import os
import pathlib

import click

from imgtools.dicom.crawl import Crawler
from imgtools.logging import logger

cpu_count: int | None = os.cpu_count()
DEFAULT_WORKERS: int = cpu_count - 2 if cpu_count is not None else 1


@click.command(no_args_is_help=True)
@click.argument(
    "source_directory",
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        path_type=pathlib.Path,
        resolve_path=True,
    ),
)
@click.option(
    "--output-json",
    type=click.Path(
        dir_okay=False,
        writable=True,
        path_type=pathlib.Path,
        resolve_path=True,
    ),
    required=False,
    help="Path to the output JSON file.",
)
@click.option(
    "--output-csv",
    type=click.Path(
        dir_okay=False,
        writable=True,
        path_type=pathlib.Path,
        resolve_path=True,
    ),
    required=False,
    help="Path to the output CSV file.",
)
@click.option(
    "--dataset-name",
    type=str,
    required=False,
    help="If outputs are not provided the dataset name will be used to create the output file names.",
    default=None,
)
@click.option(
    "-j",
    "--num-workers",
    type=int,
    default=DEFAULT_WORKERS,
    show_default=True,
    help="Number of worker processes to use for multiprocessing.",
)
@click.option(
    "--update",
    is_flag=True,
    help="Force run a crawl, updating existing records in the database.",
)
@click.help_option(
    "-h",
    "--help",
)
def index(
    source_directory: pathlib.Path,
    output_json: pathlib.Path | None,
    output_csv: pathlib.Path | None,
    dataset_name: str | None,
    num_workers: int,
    update: bool,
) -> None:
    """
    Index all DICOM files in SOURCE_DIRECTORY and save the database
    in JSON and CSV format.

    If OUTPUT_JSON and OUTPUT_CSV are not provided, the database will be saved
    in a `.imgtools` directory in the SOURCE_DIRECTORY's parent directory.
    """
    logger.info(
        f"Indexing DICOM files in {source_directory} with {num_workers} worker(s)."
    )

    if dataset_name and (output_json or output_csv):
        logger.warning(
            'Output Files explicitly provided. Ignoring "dataset-name" argument.'
        )

    _crawler = Crawler(
        dicom_dir=source_directory,
        dcm_extension="dcm",
        dataset_name=dataset_name,
        db_json=output_json,
        db_csv=output_csv,
        n_jobs=num_workers,
        force=update,
    )

    logger.info("Indexing complete.")


if __name__ == "__main__":
    index()
