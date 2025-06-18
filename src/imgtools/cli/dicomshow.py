
import click

from imgtools.loggers import logger

@click.command(no_args_is_help=True)
@click.argument(
    "dicom_file",
    type=str,
    metavar="FILE_PATH[::FIELD]",
)
@click.option(
    "--pydicom", "-p",
    is_flag=True,
    default=False,
    help="Use raw pydicom implementation instead of enhanced metadata extraction. "
         "Faster but excludes computed fields.",
)
@click.option(
    "--no-progress",
    is_flag=True,
    default=False,
    help="Disable progress bars when displaying large files. "
         "Use this when piping output or in scripts.",
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
    """Display and extract DICOM file metadata in a readable table format.

    \b
    FILE_PATH[::FIELD] specifies what to display:
      - FILE_PATH: Show all metadata from the DICOM file
      - FILE_PATH::FIELD: Extract only the specified field
    
    \b
    FIELD syntax options:
      • Standard tag names: Modality, PatientName, SeriesDescription
      • Nested tags: tag.nested_tag
      • Array indexing: tag[0]
      • Combining methods: tag[0].nested_tag
      • DICOM hex tags: (0008,0060) for modality
    
    \b
    Examples:
      imgtools dicomshow scan.dcm                        # Show all metadata
      imgtools dicomshow scan.dcm::Modality              # Show only the modality
      imgtools dicomshow scan.dcm::PatientName           # Extract patient name
      imgtools dicomshow scan.dcm::SequenceItem[0].Value # Access sequence data
      imgtools dicomshow scan.dcm::(0010,0010)           # Use standard DICOM tag
    
    Output is formatted as a color-coded table with field names and values."""
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
    