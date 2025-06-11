
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
    help="Use pydicom implementation, which does not include computed fields.",
)
@click.option(
    "--no-progress",
    is_flag=True,
    default=False,
    help="Disable progress bars. Useful for piping output.",
)
@click.help_option(
    "-h",
    "--help",
)
def dicomshow(
    dicom_file: str,
    pydicom: bool = False,
    no_progress: bool = False,
) -> None:
    """Extracts and displays the metadata associated with a single dicom file.
    
        positional arguments:
            path    Path to the dicom metadata in the following format `FILE_PATH::FIELD`
                    where `FILE_PATH` is a filepath to a dicom file. 
                    Optionally, If the `::FIELD` suffix is present, then only extract the metadata value of `FIELD`.
                    `FIELD` supports accessing nested tags as well as the individual elements of a multivalue, sequence 
                    or list element.
                    
                    Examples:
                    
                    `imgtools dicomshow your_dicom.dcm::specific_tag`
                    Acesses and returns the value of `specific_tag` in `your_dicom.dcm`.
                    
                    `imgtools dicomshow your_dicom.dcm::specific_tag[0].nested_tag`
                    This accesses the first element of `specific_tag` and returns the value of `nested_tag`."""
    from pydicom import dcmread
    from pydicom.dataset import FileDataset
    from pydicom.sequence import Sequence
    from pydicom.multival import MultiValue
    import re
    from typing import Union, Any
    from rich import print
    from rich.table import Table
    from rich.markup import escape
    from imgtools.dicom.dicom_metadata import extract_metadata
    from tqdm import tqdm


    # Separate file path from tags
    split_input = dicom_file.split("::", 1) # separate file path from tags
    file_path = split_input[0] 
    tags: list[Union[int, str, tuple[int, int]]] = [] 
    if len(split_input)>1: # Check if any tags were specified
        parts = split_input[1].split('.') # separate tags
        for part in parts:
            # Determine if part is a tag name or a hexidecimal tag number.
            
            if part and part[0] == '(':
                # brackets indicate this is a hexidecimal tag number of the form (x, y). 
                # Use regex to parse the values of x and y
                match = re.search(r"\(([0-9A-Fa-f]{4}),\s*([0-9A-Fa-f]{4})\)", part)
                if match:
                    # convert from string to hexidecimal int and add to list of tags. 
                    tags.append((int(match.group(1), 16), int(match.group(2), 16)))
            else:
                # get the tag name, ignore the index if present.
                tags.append(part.split('[')[0])
            # use regex to parse the index number from the square brackets if they are present
            match = re.search(r'\[(\d+)\]', part)
            if match:
                #add the index to tags if present.
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
            raise click.ClickException(f"Cannot read DICOM file: {e}") from e

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
            for data_element in (result.iterall() if no_progress else tqdm(result.iterall(), desc="Printing Table")):
                
                tag = data_element.keyword
                
                val: Any = data_element.value
                if isinstance(val, (list, Sequence, MultiValue)):
                    table.add_row(str(tag), f"[orchid1]{val.__class__.__name__}[magenta] of length {len(val)}")
                elif isinstance(val, bytes):
                    table.add_row(str(tag), "[orchid1]Raw Byte Data")
                elif str(val) == "":
                    table.add_row(str(tag), "[orchid1][italic]empty")
                else:
                    table.add_row(str(tag), escape(str(val)))
    
    else: 

        result = extract_metadata(file_path)
        if tags:
            try:
                for tag in tags:
                    result = result[str(tag)]
            except KeyError as e:
                logger.error(f"Failed to extract tag {split_input[1]}: {e}")
                raise click.ClickException(f"Tag extraction failed: {e}") from e
            table.add_row(split_input[1], str(result))
        else: 
            for key in (result if no_progress else tqdm(result, desc="Printing Table")):
                if isinstance(result[key], list):
                    table.add_row(str(key), f"{sorted(result[key])}")
                elif result[key] != "":
                    table.add_row(str(key), str(result[key])) 
    print(table)
    logger.info("Extraction complete.")
    