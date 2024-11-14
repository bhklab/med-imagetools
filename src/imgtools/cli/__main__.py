import click
from imgtools.logging import logger
from imgtools.cli.crawl import main as crawl


def set_logging_level(verbosity: int):
    """Sets logging level based on verbosity count."""
    levels = {0: "ERROR", 1: "WARNING", 2: "INFO", 3: "DEBUG"}
    level = levels.get(verbosity, "DEBUG")  # Default to DEBUG if verbosity is high
    logger.setLevel(level)


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity level (use up to 3 times for maximum verbosity).",
)
def cli(verbose):
    set_logging_level(verbose)
    pass


cli.add_command(crawl, name="crawl")

if __name__ == "__main__":
    cli()
