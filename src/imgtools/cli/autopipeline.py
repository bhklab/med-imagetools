import click
import yaml
from pathlib import Path
from typing import Tuple
from enum import Enum
from imgtools.loggers import logger

# Redfining these here to lazy load them later
# we should rename this to be intuitive
class ROIMatchStrategy(str, Enum):  # noqa: N801
    """Enum for ROI handling strategies."""

    # merge all ROIs with the same key
    MERGE = "merge"

    # for each key, keep the first ROI found based on the pattern
    KEEP_FIRST = "keep_first"

    # separate all ROIs
    SEPARATE = "separate"


class ROIMatchFailurePolicy(str, Enum):
    """Policy for how to handle total match failure (when no ROIs match any patterns)."""

    # Ignore the issue and continue silently
    IGNORE = "ignore"

    # Log a warning but continue execution
    WARN = "warn"

    # Raise an error and halt execution
    ERROR = "error"

existing_file_modes = ["overwrite", "skip", "fail"]


def parse_spacing(ctx, param, value):
    """Parse spacing as a tuple of floats."""
    if not value:
        return (0.0, 0.0, 0.0)
    try:
        parts = value.split(",")
        if len(parts) != 3:
            raise click.BadParameter("Spacing must be three comma-separated values")
        return tuple(float(p) for p in parts)
    except ValueError:
        raise click.BadParameter("Spacing values must be valid floats")


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
    "--filename-format",
    "-f",
    type=str,
    metavar="FORMAT",
    show_default=True,
    default="{SampleNumber}__{PatientID}/{Modality}_{SeriesInstanceUID}/{ImageID}.nii.gz", 
    help="Format string for output filenames with placeholders for metadata values"
)
@click.option(
    "--modalities", 
    "-m",
    type=str,
    required=True, 
    help="List of modalities to include"
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
    help="Resampling spacing as comma-separated values i.e '--spacing 1.0,1.0,1.0'"
)
@click.option(
    "--window", 
    type=float, 
    default=None, 
    help="Window value for intensity windowing"
)
@click.option(
    "--level", 
    type=float, 
    default=None, 
    help="Level value for intensity windowing"
)
@click.option(
    "--roi-ignore-case", 
    is_flag=True, 
    default=True, 
    help="Ignore case in ROI matching"
)
@click.option(
    "--roi-strategy", 
    type=click.Choice([s.name for s in ROIMatchStrategy]), 
    default="MERGE",
    show_default=True,
    help="Strategy for handling ROI matches"
)
@click.option(
    "--roi-allow-multi-matches", 
    is_flag=True, 
    default=True, 
    show_default=True,
    help="Allow one ROI to match multiple keys in the match map"
)
@click.option(
    "--roi-on-missing-regex", 
    type=click.Choice([p.name for p in ROIMatchFailurePolicy]), 
    default="WARN",
    show_default=True,
    help="How to handle when no ROI matches any pattern"
)
@click.option(
    "--roi-match-map", 
    "-r",
    multiple=True, 
    help="ROI matching patterns in format 'key:pattern1,pattern2,...'"
)
@click.option(
    "--roi-match-yaml", 
    type=click.Path(file_okay=True, dir_okay=False, readable=True, path_type=Path, resolve_path=True),
    default=None,
    show_default=True,
    help="Path to ROI YAML file."
)
@click.option(
    "--first-n", 
    type=int, 
    default=None, 
    help="Process only the first N samples"
)
@click.help_option(
    "-h",
    "--help",
)
def autopipeline(
    input_directory: str,
    output_directory: str,
    filename_format: str,
    existing_file_mode: str,
    update_crawl: bool,
    jobs: int,
    modalities: str,
    spacing: Tuple[float, float, float],
    window: float,
    level: float,
    roi_ignore_case: bool,
    roi_strategy: str,
    roi_allow_multi_matches: bool,
    roi_on_missing_regex: str,
    roi_match_map: Tuple[str],
    roi_match_yaml: Path,
    first_n: int
):
    """
    Run the DeltaPipeline for processing medical images.
    
    This command allows you to process medical images in a directory structure,
    apply transformations, and save the results to a specified output directory.
    """
    # Parse ROI match map
    roi_map = {}
    
    # Load from YAML file if provided
    if roi_match_yaml:
        try:
            with open(roi_match_yaml, 'r') as f:
                yaml_data = yaml.safe_load(f)
                if not isinstance(yaml_data, dict):
                    raise click.BadParameter(f"ROI match YAML must contain a dictionary")
                roi_map = yaml_data
        except Exception as e:
            raise click.BadParameter(f"Error reading ROI match YAML file: {str(e)}")
    
    # Add CLI-provided mappings (these take precedence over YAML)
    if roi_match_map:
        for mapping in roi_match_map:
            parts = mapping.split(":", 1)
            if len(parts) != 2:
                raise click.BadParameter(f"Invalid ROI match map format: {mapping}")
            key, patterns = parts
            roi_map[key] = patterns.split(",")

    from imgtools.autopipeline import DeltaPipeline
    from imgtools.io.sample_output import ExistingFileMode
    # Create the pipeline
    pipeline = DeltaPipeline(
        input_directory=input_directory,
        output_directory=output_directory,
        output_filename_format=filename_format,
        existing_file_mode=ExistingFileMode[existing_file_mode.upper()],
        update_crawl=update_crawl,
        n_jobs=jobs,
        modalities=list(modalities.split(",")),
        roi_match_map=roi_map if roi_map else None,
        roi_ignore_case=roi_ignore_case,
        roi_handling_strategy=ROIMatchStrategy[roi_strategy],
        roi_allow_multi_key_matches=roi_allow_multi_matches,
        roi_on_missing_regex=ROIMatchFailurePolicy[roi_on_missing_regex],
        spacing=spacing,
        window=window,
        level=level,
    )
    
    # # Run the pipeline
    # try:
    #     results = pipeline.run(first_n=first_n)
    # except Exception as e:
    #     logger.exception(f"Error running pipeline: {str(e)}")
    #     raise click.Abort()
    # click.echo(f"Processed {len(results)} samples.")


if __name__ == "__main__":
    autopipeline()