# pragma: skip-file
import click
from rich import print  # noqa

from imgtools.dicom.dicom_metadata import (
    extract_metadata,
    get_keys_from_modality,
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
@click.option("--list-tags", "-lt", help="List tags for a given modality")
def cli(dicom_file, output, list_modalities, list_tags) -> None:  # type: ignore # noqa
    """Extract DICOM metadata from a file."""
    modalities = supported_modalities()
    if list_modalities:
        print("Available DICOM modalities:")
        for modality in modalities:
            print(modality)
        return

    if list_tags:
        if list_tags not in modalities:
            print(
                f"Modality '{list_tags}' is not supported. Returning generic"
            )
        tags = get_keys_from_modality(list_tags)
        print(f"Available tags for {list_tags}:")
        for tag in tags:
            print(tag)
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
