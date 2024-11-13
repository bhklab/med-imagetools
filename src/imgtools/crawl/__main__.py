import click
import pathlib
from imgtools.crawl.crawl import crawl_directory
from imgtools.logging import logger
import json

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
    
    # Save list of dicts to JSON file
    output = pathlib.Path("database.json")
    with open(output.as_posix(), "w") as f:
        logger.debug("Saving database to JSON file...", file=output)
        f.write(json.dumps(db, indent=4))



if __name__ == "__main__":
    main()
