from pathlib import Path
from typing import Tuple

import click
import yaml

from imgtools.loggers import logger

# TODO:: think of a smarter way to handle this,
# perhaps only try loading autopipeline cli help if the user
# is using it, would need to modify click.Command to do this
# Redfining these here to lazy load them later


def parse_spacing(ctx, param, value): # type: ignore # noqa
    """Parse spacing as a tuple of floats."""
    if not value:
        return (0.0, 0.0, 0.0)
    try:
        parts = value.split(",")
        if len(parts) != 3:
            raise click.BadParameter("Spacing must be three comma-separated values")
        return tuple(float(p) for p in parts)
    except ValueError:
        raise click.BadParameter("Spacing values must be valid floats") from ValueError


existing_file_modes = ["overwrite", "skip", "fail"]


@click.command(no_args_is_help=True)
@click.argument(
    "input_directory",
    type=click.Path(
        file_okay=False, dir_okay=True, writable=True, path_type=Path, resolve_path=True, exists=True
    ),
)
@click.argument(
    "output_directory",
    type=click.Path(
        file_okay=False, dir_okay=True, writable=True, path_type=Path, resolve_path=True
    ),
)
@click.option(
    "--modalities", 
    "-m",
    type=str,
    required=True, 
    help=(
        "List of modalities to process, in hierarchical order."
        " For example, '--modalities CT,RTSTRUCT' or '--modalities MR,SEG'"
    )
)
@click.option(
    "--roi-match-yaml", 
    "-ryaml",
    required=True,
    type=click.Path(file_okay=True, dir_okay=False, readable=True, path_type=Path, resolve_path=True),
    help="Path to YAML file containing ROI matching patterns."
)
@click.option(
    "--mask-saving-strategy",
    "-ms",
    type=click.Choice(["label_image", "sparse_mask", "region_mask"]),
    default="label_image",
    help="Strategy for saving masks."
)
@click.option(
    "--existing-file-mode", 
    type=click.Choice(existing_file_modes), 
    default="fail",
    help="How to handle existing files"
)
@click.option(
    "--update-crawl", 
    is_flag=True, 
    help="Force recrawling of the input directory"
)
@click.option(
    "--jobs", 
    "-j", 
    type=int, 
    default=None, 
    help="Number of parallel jobs"
)
@click.option(
    "--spacing", 
    callback=parse_spacing, 
    default="0.0,0.0,0.0",
    show_default=True,
    help="Resampling spacing as comma-separated values i.e '--spacing 1.0,1.0,1.0'"
)
@click.option(
    "--window-width",
    "window", 
    type=float, 
    default=None, 
    help="Width of the window for intensity windowing"
)
@click.option(
    "--window-level",
    "level",
    type=float, 
    default=None, 
    help="Midpoint of the window for intensity windowing"
)
@click.option(
    "--roi-ignore-case/--roi-case-sensitive",  
    default=True,
    help="Perform case‑insensitive ROI matching (default: enabled)",  
)
@click.option(  
    "--roi-allow-multi-matches/--roi-disallow-multi-matches",  
    default=True,  
    show_default=True,  
    help="Allow one ROI to match multiple keys in the match map"  
)
@click.help_option(
    "-h",
    "--help",
)
def nnunet_pipeline(
    input_directory: str,
    output_directory: str,
    modalities: str,
    roi_match_yaml: Path,
    mask_saving_strategy: str,
    existing_file_mode: str,
    update_crawl: bool,
    jobs: int,
    spacing: Tuple[float, float, float],
    window: float,
    level: float,
    roi_ignore_case: bool,
    roi_allow_multi_matches: bool,
) -> None:
    """Process medical images in nnUNet format.
    
    This command allows you to process medical images in the nnUNet directory structure,
    apply transformations, and save the results to a specified output directory.

    \b
    INPUT_DIRECTORY: Directory containing the input images.
    OUTPUT_DIRECTORY: Directory to save the processed images.

    \b
    - SampleNumber: The identifier for the sample after querying.
    - PatientID: The ID of the patient.
    - Modality: The imaging modality (e.g., CT, MRI).
    - SeriesInstanceUID: The unique identifier for the series.
    - ImageID: The cutomized identifier for the image.
        - By default, the modality of the image
        - If RTSTRUCT or SEG, uses custom format based on the roi_strategy
            roi_match_map and roi names.
        TODO:: explain this in the docs?

    """
    # Parse ROI match map
    roi_map = {}
    
    # Load from YAML file if provided
    try:
        with roi_match_yaml.open('r') as f:
            yaml_data = yaml.safe_load(f)
            if not isinstance(yaml_data, dict):
                raise click.BadParameter("ROI match YAML must contain a dictionary")
            roi_map = yaml_data
    except Exception as e:
        msg = f"Error reading ROI match YAML file: {str(e)}"
        raise click.BadParameter(msg) from e 

    logger.debug(f"ROI match map: {roi_map}")

    from imgtools.io.nnunet_output import MaskSavingStrategy
    from imgtools.io.sample_output import ExistingFileMode
    from imgtools.nnunet_pipeline import nnUNetPipeline
    # Create the pipeline
    pipeline = nnUNetPipeline(
        input_directory=input_directory,
        output_directory=output_directory,
        modalities=list(modalities.split(",")),
        roi_match_map=roi_map,
        mask_saving_strategy=MaskSavingStrategy(mask_saving_strategy),
        existing_file_mode=ExistingFileMode[existing_file_mode.upper()],
        update_crawl=update_crawl,
        n_jobs=jobs,
        roi_ignore_case=roi_ignore_case,
        roi_allow_multi_key_matches=roi_allow_multi_matches,
        spacing=spacing,
        window=window,
        level=level,
    )
    
    # Run the pipeline
    try:
        _ = pipeline.run()
    except Exception as e:
        logger.exception(f"Error running pipeline: {str(e)}")
        raise click.Abort() from e

if __name__ == "__main__":
    nnunet_pipeline()