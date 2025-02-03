import pathlib
from typing import List

import click


def is_testdata_available() -> bool:
    try:
        from github import Github  # type: ignore # noqa

        return True
    except ImportError:
        return False


if is_testdata_available():
    from imgtools.datasets import MedImageTestData


@click.command(
    no_args_is_help=True,
)
@click.argument(
    "dest",
    type=click.Path(
        exists=False,
        file_okay=False,
        dir_okay=True,
        writable=True,
        path_type=pathlib.Path,
        resolve_path=True,
    ),
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
def testdata(dest: pathlib.Path, assets: List[str], no: List[str]) -> None:
    """Download test data from the latest GitHub release.

    DEST is the directory where the test data will be saved.

    assets can be one of the following:

    \b
    - 4D-Lung.tar.gz
    - CC-Tumor-Heterogeneity.tar.gz
    - NSCLC-Radiomics.tar.gz
    - NSCLC_Radiogenomics.tar.gz
    - QIN-PROSTATE-Repeatability.tar.gz
    - Soft-tissue-Sarcoma.tar.gz
    - Vestibular-Schwannoma-SEG.tar.gz

    """
    manager = MedImageTestData()
    selected_assets = None

    if assets:
        selected_assets = [
            asset for asset in manager.datasets if asset.name in assets
        ]
        if not selected_assets:
            click.echo(f"No matching assets found for: {', '.join(assets)}")
            return

    downloaded_files = manager.download(
        dest, assets=selected_assets, exclude=no
    )
    # click.echo(
    #     f"Downloaded files: {', '.join(str(file) for file in downloaded_files)}"
    # )
    click.echo("Downloaded files:")
    for file in downloaded_files:
        click.echo(f"\t{file}")


if __name__ == "__main__":
    testdata()
