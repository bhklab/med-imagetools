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
@click.option(
    "--query-string", "-q",
    type=str,
    default=None,
    help="""Comma-separated string of modalities to query (e.g., 'CT,MR').
            
            Supported modalities: CT, PT, MR, SEG, RTSTRUCT, RTDOSE.
            
            """,
)
@click.option(
    "--group-by-root", "-g",
    type=bool,
    default=True,
    help="""If True, group the returned dicoms by their root CT/MR/PT
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
def interlacer(path: Path,
               query_string: str,
               group_by_root: bool,
               n_jobs: int,
               force: bool) -> None:
    """Visualize DICOM series relationships after indexing.

    This command will print the tree hierarchy of DICOM series relationships
    similar to GNU/Linux `tree` command.

    Only shows supported modalities.

    \b
    `interlacer PATH will print the series tree for the given index file / directory.

    If PATH is a path to an index.csv file, then the tree will be constructed using that index file.
    If instead PATH is a path to a directory, if the an index file for the directory exists it will be used to contruct the tree, 
    otherwise the directory will be crawled first.

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
    from imgtools.dicom.interlacer import Interlacer, print_interlacer_tree, SeriesNode
    if (path.is_file() and force):
        logger.warning(f"force requires a directory as input. {path} will be used as the index.")
    
    if (path.is_file() and n_jobs != DEFAULT_WORKERS):
        logger.warning(f"n_jobs requires a directory as input. {path} will be used as the index.")

    elif (path.is_dir()):
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
        if crawler._crawl_results is not None:
            path = crawler._crawl_results.index_csv_path
        else:
            logger.exception("Failed to crawl directory.")
            raise click.Abort()


    interlacer = Interlacer(path)
    if query_string is None:
        interlacer.print_tree(None)
    else:
        try:
            result = interlacer.query(query_string=query_string, group_by_root=group_by_root)
        except Exception as e:
            logger.exception("Failed to query interlacer.")
            raise click.Abort() from e

        # Update root node children to reflect query structure instead of overall index structure
        for group in result:
            group[0].children = group[1:]
            for node in group[1:]:
                node.children = []
          
        root_nodes = [group[0] for group in result]

        print_interlacer_tree(root_nodes, input_directory=None)