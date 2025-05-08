import click
import os
from pathlib import Path
from imgtools.loggers import logger

cpu_count: int | None = os.cpu_count()
DEFAULT_WORKERS: int = cpu_count - 2 if cpu_count is not None else 1

@click.command(no_args_is_help=True)
@click.argument(
    "file_path",
    type=click.Path(
        exists=True, path_type=Path, dir_okay=True, file_okay=True
    ),
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
@click.help_option("--help", "-h")
def interlacer(file_path: Path,
               n_jobs: int,
               force: bool) -> None:
    """Visualize DICOM series relationships after indexing.

    This command will print the tree hierarchy of DICOM series relationships
    similar to GNU/Linux `tree` command.

    Only shows supported modalities.

    \b
    `interlacer INDEX_FILE will print the series tree for the given index file.

    \b
    The index file should be a CSV file with the following columns:
    - SeriesInstanceUID
    - Modality
    - PatientID
    - StudyInstanceUID
    - folder
    - ReferencedSeriesUID

    \b
    Visit https://bhklab.github.io/med-imagetools/ for more information.
    """
    from imgtools.dicom.interlacer import Interlacer
    if (file_path.is_file() and force):
        logger.warning(f"force requires a directory as input. {file_path} will be used as the index.")

    elif (file_path.is_dir()):
        if (force or not (file_path.parent / ".imgtools" / file_path.name / "index.csv").exists()):
            from imgtools.dicom.crawl import Crawler
            crawler = Crawler(
                dicom_dir=file_path,
                n_jobs=n_jobs,
                force=force,
                )
            crawler.crawl()
            logger.info("Crawling completed.")
            logger.info("Crawl results saved to %s", crawler.output_dir)
        file_path = file_path = file_path.parent / ".imgtools" / file_path.name / "index.csv"


    interlacer = Interlacer(file_path)
    interlacer.print_tree(None)