import os

import click
from pathlib import Path

from imgtools.loggers import logger

cpu_count: int | None = os.cpu_count()
DEFAULT_WORKERS: int = cpu_count - 2 if cpu_count is not None else 1


@click.command(no_args_is_help=True)
@click.option(
    "--dicom-dir",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to the DICOM directory.",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to the output directory. If not specified, a directory named '.imgtools' will be created in the parent directory of the DICOM directory.",
)
@click.option(
    "--dataset-name",
    type=str,
    default=None,
    help="Name of the dataset. If not specified, the name of the DICOM directory will be used.",
)
@click.option(
    "--n-jobs",
    type=int,
    default=DEFAULT_WORKERS,
    help="Number of jobs to use for parallel processing.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Force overwrite existing files.",
)
@click.help_option(
    "-h",
    "--help",
)
def index(
    dicom_dir: Path,
    output_dir: Path | None,
    dataset_name: str | None,
    n_jobs: int,
    force: bool,
) -> None:
    """Crawl DICOM directory and create a database index.

    - looks for all DICOM files in the specified directory, extracts metadata, 
        and builds a comprehensive index of the dataset.

    - The index includes information about the series, modalities, and other
        relevant details, making it easier to manage and analyze the DICOM files.

    - The output is saved in a structured format, including JSON and CSV files,
        which can be used for further processing or analysis.
    
    - By default, it saves the results in a ".imgtools" folder right next to 
        your DICOM directory, but you can pick your own place to store them.
    """
    from imgtools.dicom.crawl import Crawler, CrawlerOutputDirError
    crawler = Crawler(
        dicom_dir=dicom_dir,
        output_dir=output_dir,
        dataset_name=dataset_name,
        n_jobs=n_jobs,
        force=force,
    )
    try:
        crawler.crawl()
    except CrawlerOutputDirError as e:
        logger.exception("Output directory error")
        # exit with a non-zero status code
        raise click.ClickException(f"Output directory error: {e}") from e
    except Exception as e:
        logger.exception("Unknown Crawling Error has occurred")
        # exit with a non-zero status code
        raise click.ClickException(f"Crawling failed") from e
    else:
        logger.info("Crawling completed successfully.")
        logger.info("Crawl results saved to %s", crawler.output_dir)

if __name__ == "__main__":
    index()
