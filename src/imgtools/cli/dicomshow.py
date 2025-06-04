
import click

from imgtools.loggers import logger

@click.command(no_args_is_help=True)
@click.argument(
    "dicom_file",
    type=str,
)
@click.option(
    "--pydicom", "-p",
    is_flag=True,
    default=False,
    help="Use pydicom implementation, which does not include computed fields."
)
@click.help_option(
    "-h",
    "--help",
)
def dicomshow(
    dicom_file: str,
    pydicom: bool = False,
) -> None:
    """Extracts and displays the metadata associated with a single dicom file."""
    from pydicom import dcmread
    from pydicom.dataset import FileDataset
    from pydicom.dataelem import DataElement
    from pydicom.sequence import Sequence
    from pydicom.multival import MultiValue
    import re
    from typing import Union, Any
    from rich import print
    from rich.table import Table
    from rich.markup import escape
    from imgtools.dicom.dicom_metadata import extract_metadata
    from tqdm import tqdm

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

    table = Table(title=f"", box=None)
    table.add_column("Keyword", justify="left", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")
    
    if pydicom:

        try:
            logger.info(f"Extracting tags from {dicom_file} (pydicom method)")
            result: Any = dcmread(file_path, stop_before_pixels=True)
        except Exception as e:
            logger.error(f"Failed to read DICOM file {file_path}: {e}")
            raise click.ClickException(f"Cannot read DICOM file: {e}")

        if tags:
            try:
                for tag in tags:
                    if isinstance(tag, int):
                        result = result[tag]
                    else:
                        if not isinstance(result, FileDataset):
                            raise ValueError("Cannot access tag by name on non-dataset object")
                        result = result.get(tag)
                table.add_row(split_input[1], escape(str(result)))
            except (KeyError, IndexError, ValueError) as e:
                logger.error(f"Failed to extract tag {split_input[1]}: {e}")
                raise click.ClickException(f"Tag extraction failed: {e}")
        else:
            if not isinstance(result, FileDataset):
                raise click.ClickException("Expected DICOM dataset for metadata extraction")
            for data_element in tqdm(result.iterall()):
                
                tag = data_element.keyword
                
                val: Any = data_element.value
                if isinstance(val, list) or isinstance(val, Sequence) or isinstance(val, MultiValue):
                   table.add_row(str(tag), f"[orchid1]{val.__class__.__name__}[magenta] of length {len(val)}") 
                elif isinstance(val, bytes):
                    table.add_row(str(tag), f"[orchid1]Raw Byte Data")
                elif str(val) == "":
                    table.add_row(str(tag), f"[orchid1][italic]empty")
                else:
                    table.add_row(str(tag), escape(str(val)))
    
    else: 

        result = extract_metadata(file_path)
        if tags:
            for tag in tqdm(tags):
                result = result[str(tag)]
            table.add_row(split_input[1], str(result))
        else: 
            for key in tqdm(result):
                if isinstance(result[key], list):
                    table.add_row(str(key), f"{sorted(result[key])}")
                elif result[key] != "":
                    table.add_row(str(key), str(result[key])) 
    print(table)
    logger.info("Extraction complete.")
    