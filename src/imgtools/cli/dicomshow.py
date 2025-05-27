from pathlib import Path
import re
from typing import List
from rich import print
from rich.table import Table
import click

from imgtools.loggers import logger

@click.command(no_args_is_help=True)
@click.argument(
    "dicom_file",
    type=str,
)
@click.option(
    "-m",
    "--modality",
    default=None,
    type=str,
    show_default=True,
    help="Optionally specify the modality of the dicom, if modality is not specified it will be automatically determined. ",
)
@click.help_option(
    "-h",
    "--help",
)
def dicomshow(
    dicom_file: str,
    modality: str,
) -> None:
    """Extracts and displays the metadata associated with a single dicom file."""
    from pydicom import dcmread
    from pydicom.dataset import FileDataset
    import re

    split_input = dicom_file.split("::", 1)
    file_path = split_input[0]
    tags = []
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

    print(f"[blue]{tags}")


    logger.info(f"Extracting tags from {dicom_file}")
    result = dcmread(file_path, stop_before_pixels=True)
    table = Table(title=f"[gold1]{dicom_file}", box=None)
    table.add_column("Keyword", justify="left", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")
    

    if tags:
        for tag in tags:
            if type(tag) is int:
                result = result[tag]
                print(f"[red]{result.keys()}\n\n[blue]{result.values()}")
            else:
                result = result.get(tag)
        table.add_row(split_input[1], str(result))
    else:
        
        for key in result.keys():
            row = result.get(key, default="")
            tag = row.keyword
            val = str(row.value)
            table.add_row(str(tag), val)
    print(table)
    logger.info(f"Extraction complete.")

    