import click
from rich import print  # noqa

from imgtools.dicom.dicom_metadata import (
    extract_metadata,
    supported_modalities,
)


@click.command()
@click.argument("dicom_file", type=click.Path(exists=True))
@click.option(
    "-o",
    "--output",
    type=click.Path(writable=True),
    default=None,
    help="Output file path for the extracted metadata.",
)
@click.option(
    "--list-modalities",
    "-lm",
    is_flag=True,
    help="List all available DICOM modalities.",
)
def cli(dicom_file, output, list_modalities):
    """Extract DICOM metadata from a file."""
    if list_modalities:
        modalities = supported_modalities()
        print("Available DICOM modalities:")
        for modality in modalities:
            print(modality)
        return

    metadata = extract_metadata(dicom_file)

    if output:
        from pathlib import Path

        with Path(output).open("w") as f:
            f.write(str(metadata))
    else:
        print(metadata)


if __name__ == "__main__":
    cli()
