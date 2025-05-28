
import click

from imgtools.loggers import logger

@click.command(no_args_is_help=True)
@click.argument(
    "dicom_file",
    type=str,
)
@click.help_option(
    "-h",
    "--help",
)
def dicomshow(
    dicom_file: str,
) -> None:
    """Extracts and displays the metadata associated with a single dicom file."""
    from pydicom import dcmread
    from pydicom.dataset import FileDataset
    from pydicom.dataelem import DataElement
    import re
    from typing import Union
    from rich import print
    from rich.table import Table

    split_input = dicom_file.split("::", 1)
    file_path = split_input[0]
    tags: list[Union[int, str, tuple[int, int]]] = []
    if len(split_input)>1:
        parts = split_input[1].split('.')
        for part in parts:
            if part[0] == '(':
                match = re.search(r"\(([0-9A-Fa-f]{4}),\s*([0-9A-Fa-f]{4})\)", part)
                if match:
                    tags.append((int(match.group(1), 16), int(match.group(2), 16)))
            else:
                tags.append(part.split('[')[0])
            match = re.search(r'\[(\d+)\]', part)
            if match:
                tags.append(int(match.group(1)))



    try:
        logger.info(f"Extracting tags from {dicom_file}")
        result: Union[FileDataset, DataElement] = dcmread(file_path, stop_before_pixels=True)
    except Exception as e:
        logger.error(f"Failed to read DICOM file {file_path}: {e}")
        raise click.ClickException(f"Cannot read DICOM file: {e}")

    table = Table(title=f"[gold1]{dicom_file}", box=None)
    table.add_column("Keyword", justify="left", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")

    if tags:
        try:
            for tag in tags:
                if isinstance(tag, int):
                    result = result[tag]
                else:
                    if not isinstance(result, FileDataset):
                        raise ValueError("Cannot access tag by name on non-dataset object")
                    result = result.get(tag)
            table.add_row(split_input[1], str(result))
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Failed to extract tag {split_input[1]}: {e}")
            raise click.ClickException(f"Tag extraction failed: {e}")
    else:
        if not isinstance(result, FileDataset):
            raise click.ClickException("Expected DICOM dataset for metadata extraction")
        for data_element in result.iterall():
            tag = data_element.keyword
            val = str(data_element.value)
            table.add_row(str(tag), val)

    print(table)
    logger.info("Extraction complete.")
    