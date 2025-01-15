import click

from imgtools import __version__
from imgtools.cli import set_log_verbosity
from imgtools.cli.dicomfind import find_dicoms
from imgtools.cli.dicomsort import dicomsort
from imgtools.cli.index import index


@click.group(
    no_args_is_help=True,
)
@set_log_verbosity()
@click.version_option(
    version=__version__,
    package_name="med-imagetools",
    prog_name="imgtools",
    message="%(package)s:%(prog)s:%(version)s",
)
@click.help_option(
    "-h",
    "--help",
)
def cli(verbose: int, quiet: bool) -> None:
    """A collection of tools for working with medical imaging data."""
    pass


cli.add_command(index)
cli.add_command(dicomsort)
cli.add_command(find_dicoms, "find-dicoms")

if __name__ == "__main__":
    cli()
