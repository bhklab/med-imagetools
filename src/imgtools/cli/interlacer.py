import click
from pathlib import Path

@click.command(no_args_is_help=True)
@click.argument(
    "index_file",
    type=click.Path(
        exists=True, path_type=Path, dir_okay=False, file_okay=True
    ),
)
@click.help_option("--help", "-h")
def interlacer(index_file: Path) -> None:
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
    interlacer = Interlacer(index_file)
    interlacer.print_tree(None)