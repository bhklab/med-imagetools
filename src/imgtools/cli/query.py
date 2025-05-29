import click
import os
from pathlib import Path
from imgtools.loggers import logger

cpu_count: int | None = os.cpu_count()
DEFAULT_WORKERS: int = cpu_count - 2 if cpu_count is not None else 1

@click.command(no_args_is_help=True)
@click.argument(
    "path",
    type=click.Path(
        exists=True, path_type=Path, dir_okay=True, file_okay=True
    ),
)
@click.argument(
    "query_string",
    type=str,
)
@click.option(
    "--group-by-root",
    type=bool,
    default=True,
    help="""If True, group the returned SeriesNodes by their root CT/MR/PT
    node (i.e., avoid duplicate root nodes across results).""",
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
def query(  path: Path,
            query_string: str,
            group_by_root: bool,
            n_jobs: int,
            force: bool,
            ) -> None:

    from imgtools.dicom.interlacer import Interlacer, ModalityHighlighter, print_interlacer_tree
    from rich.console import Console

    if (path.is_file() and force):
        logger.warning(f"force requires a directory as input. {path} will be used as the index.")
    
    if (path.is_file() and n_jobs > DEFAULT_WORKERS):
        logger.warning(f"n_jobs requires a directory as input. {path} will be used as the index.")

    elif (path.is_dir()):
        index_path = path.parent / ".imgtools" / path.name / "index.csv"
        if (force or not index_path.exists()):
            from imgtools.dicom.crawl import Crawler
            logger.info("Initializing crawl.")
            try:
                crawler = Crawler(
                    dicom_dir=path,
                    n_jobs=n_jobs,
                    force=force,
                )
                crawler.crawl()
            except Exception as e:
                logger.exception("Failed to crawl directory.")
                raise click.Abort() from e
            logger.info("Crawling completed.")
            logger.info("Crawl results saved to %s", crawler.output_dir)
        path = index_path

    try:
        interlacer = Interlacer(path)
    except Exception as e:
        logger.exception("Failed to initialize interlacer.")
        raise click.Abort() from e
    
    try:
        result = interlacer.query(query_string=query_string, group_by_root=group_by_root)
    except Exception as e:
        logger.exception("Failed to query interlacer tree.")
        raise click.Abort() from e

    # Update root node children to reflect query structure instead of overall index structure
    for group in result:
        group[0].children = group[1:]
    root_nodes = [group[0] for group in result]

    print_interlacer_tree(root_nodes, input_directory=None)
