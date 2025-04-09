import pathlib
from typing import List, Pattern

import click

from imgtools.loggers import logger


def is_testdata_available() -> bool:
    try:
        from github import Github  # type: ignore # noqa
        import aiohttp  # noqa

        return True
    except ImportError:
        return False


@click.command(
    no_args_is_help=True,
    hidden=not is_testdata_available(),
)
@click.option(
    "--dest",
    "-d",
    type=click.Path(
        exists=False,
        file_okay=False,
        dir_okay=True,
        writable=True,
        path_type=pathlib.Path,
        resolve_path=True,
    ),
    help="The directory where the test data will be saved.",
)
@click.option(
    "-a",
    "--assets",
    multiple=True,
    help="Specific assets to download. If not provided, all assets will be downloaded.",
)
@click.option("--no", multiple=True, help="Assets to exclude from download.")
@click.help_option(
    "-h",
    "--help",
)
@click.option(
    "--list-assets",
    "-l",
    is_flag=True,
    help="List available assets and exit.",
)
def testdata(
    dest: pathlib.Path,
    assets: List[str],
    no: List[Pattern[str]],
    list_assets: bool,
) -> None:
    """Download test data from the latest GitHub release."""

    try:
        from imgtools.datasets import MedImageTestData
    except ImportError:
        click.echo(
            "The test datasets are not available. "
            "Please install the required dependencies using: `pip install imgtools[datasets]`."
        )
        return
    manager = MedImageTestData()

    if list_assets:
        click.echo("Available assets:")
        for asset in manager.dataset_names:
            click.echo(f"\t{asset}")
        return

    if not dest:
        click.echo("Destination directory (--dest) is required.")
        return

    logger.debug(f"Available assets: {manager.dataset_names}")

    if assets:
        selected_assets = [
            asset for asset in manager.datasets if asset.label in assets
        ]
        if not selected_assets:
            click.echo(f"No matching assets found for: {', '.join(assets)}")
            return
    else:
        selected_assets = None

    downloaded_files = manager.download(
        dest, assets=selected_assets, exclude=no
    )

    click.echo("Downloaded files:")
    for file in downloaded_files:
        click.echo(f"\t{file}")


if __name__ == "__main__":
    testdata()
