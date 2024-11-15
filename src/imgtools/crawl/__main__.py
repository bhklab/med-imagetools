import click
import pathlib
from imgtools.crawl.crawl import crawl_directory
from imgtools.logging import logger

@click.command()
@click.argument(
    "directory",
    type=click.Path(
        exists=True,
        path_type=pathlib.Path,
        resolve_path=True,
        file_okay=False,
    ),
)
def main(directory: pathlib.Path):
    logger.debug("Crawling directory...", directory=directory)
    db = crawl_directory(directory)
    print("# patients:", len(db))


if __name__ == "__main__":
    main()
