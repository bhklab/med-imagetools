import os
import pathlib

import click

# from imgtools.crawler import crawl
from imgtools.loggers import logger

cpu_count: int | None = os.cpu_count()
DEFAULT_WORKERS: int = cpu_count - 2 if cpu_count is not None else 1


@click.command()
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
    "-j",
    "--num-workers",
    type=int,
    default=DEFAULT_WORKERS,
    show_default=True,
    help="Number of worker processes to use for multiprocessing.",
)
@click.help_option(
    "-h",
    "--help",
)
def index(
    source_directory: pathlib.Path,
    num_workers: int,
) -> None:
    """Crawl a directory and index dicoms."""

    logger.info(f"Indexing images in {source_directory}.")

    # TODO: extend parameters such as csv_path, json_path, etc.
    # crawl(top=source_directory, n_jobs=num_workers)

    logger.info("Indexing complete.")
