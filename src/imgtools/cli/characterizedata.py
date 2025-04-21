import os
import sys
import platform
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

import click
import SimpleITK as sitk
import pandas as pd

from imgtools.loggers import logger
from imgtools.dicom.crawl.characterize_data import (
    inspect_files,
    inspect_series,
    image_list_to_faux_volume,
)

# Use CPU count to determine default number of workers
cpu_count: int | None = os.cpu_count()
DEFAULT_WORKERS: int = cpu_count - 2 if cpu_count is not None else 1


@click.command(no_args_is_help=True)
@click.argument(
    "root_dir", 
    type=click.Path(exists=True, path_type=Path, file_okay=False, dir_okay=True),
    required=True,
    metavar="ROOT_DIRECTORY"
)
@click.argument(
    "output_file",
    type=click.Path(path_type=Path),
    required=True,
    metavar="OUTPUT_FILE"
)
@click.argument(
    "analysis_type",
    type=click.Choice(["per_file", "per_series"]),
    required=True,
)
@click.option(
    "--max-processes",
    type=click.IntRange(min=1),
    default=DEFAULT_WORKERS,
    help="Maximal number of parallel processes.",
)
@click.option(
    "--disable-tqdm",
    is_flag=True,
    help="Disable the tqdm progress bar display.",
)
@click.option(
    "--additional-series-tags",
    multiple=True,
    default=[
        "0020|0011",
        "0018|0024",
        "0018|0050",
        "0028|0010",
        "0028|0011",
    ],
    help="Tags used to uniquely identify image files that belong to the same DICOM series.",
)
@click.option(
    "--image-io",
    default="All",
    type=click.Choice(list(sitk.ImageFileReader().GetRegisteredImageIOs()) + ["All"]),
    help="SimpleITK imageIO to use for reading (e.g. BMPImageIO).",
)
@click.option(
    "--external-applications",
    multiple=True,
    default=[],
    help="Paths to external applications.",
)
@click.option(
    "--external-applications-headings",
    multiple=True,
    default=[],
    help="Titles of the results columns for external applications.",
)
@click.option(
    "--metadata-keys",
    multiple=True,
    default=[],
    help="Inspect values of these metadata keys (DICOM tags or other keys stored in the file).",
)
@click.option(
    "--metadata-keys-headings",
    multiple=True,
    default=[],
    help="Titles of the results columns for the metadata_keys.",
)
@click.option(
    "--ignore-problems",
    is_flag=True,
    help="Problematic files/series will not be listed in the output.",
)
@click.option(
    "--create-summary-image",
    is_flag=True,
    help="Create a summary image, volume of thumbnails representing all images.",
)
@click.option(
    "--thumbnail-sizes",
    nargs=2,
    type=click.IntRange(min=1),
    default=(64, 64),
    help="Size of thumbnail images used to create summary image.",
)
@click.option(
    "--tile-sizes",
    nargs=2,
    type=click.IntRange(min=1),
    default=(20, 20),
    help="Number of thumbnail images used to create single tile in summary image.",
)
@click.option(
    "--projection-axis",
    type=click.Choice(["0", "1", "2"]),
    default="2",
    help="For 3D images, perform maximum intensity projection along this axis.",
)
@click.option(
    "--interpolator",
    type=click.Choice(["sitkNearestNeighbor", "sitkLinear", "sitkBSpline3"]),
    default="sitkNearestNeighbor",
    help="SimpleITK interpolator used to resize images when creating summary image.",
)
@click.help_option(
    "-h",
    "--help",
)
def characterizedata(
    root_dir: Path,
    output_file: Path,
    analysis_type: str,
    max_processes: int,
    disable_tqdm: bool,
    additional_series_tags: Tuple[str, ...],
    image_io: str,
    external_applications: Tuple[str, ...],
    external_applications_headings: Tuple[str, ...],
    metadata_keys: Tuple[str, ...],
    metadata_keys_headings: Tuple[str, ...],
    ignore_problems: bool,
    create_summary_image: bool,
    thumbnail_sizes: Tuple[int, int],
    tile_sizes: Tuple[int, int],
    projection_axis: str,
    interpolator: str,
) -> None:
    """Characterize images in a directory structure.

    This command inspects/characterizes images in a given directory structure.
    It recursively traverses the directories and either inspects the files
    one by one or if in DICOM series inspection mode, inspects the data on
    a per-series basis (e.g. combines all 2D images belonging to the same CT
    series into a single 3D image).

    Parameters:
    
    ROOT_DIRECTORY: Path to the root of the data directory.
    
    OUTPUT_FILE: Path to the output CSV file.
    
    ANALYSIS_TYPE: Type of analysis to perform ("per_file" or "per_series").

    Examples:
    
    \b
    # Run a generic file analysis:
    imgtools characterizedata data/ output/report.csv per_file --metadata-keys "0008|0060" --metadata-keys-headings "modality"
    
    \b
    # Run a DICOM series based analysis:
    imgtools characterizedata data/ output/report.csv per_series --max-processes 8
    """
    # Validate input parameters
    if len(external_applications) != len(external_applications_headings):
        logger.error("Number of external applications and their headings do not match.")
        sys.exit(1)
    if len(metadata_keys) != len(metadata_keys_headings):
        logger.error("Number of metadata keys and their headings do not match.")
        sys.exit(1)

    # Configure SimpleITK to work in a single threaded fashion to avoid overwhelming system resources
    sitk.ProcessObject.SetGlobalDefaultNumberOfThreads(1)

    # Convert some entries from string representation to corresponding SimpleITK values
    image_io_value = "" if image_io == "All" else image_io
    interpolator_value = getattr(sitk, interpolator)
    projection_axis_value = int(projection_axis)

    # Process thumbnail settings
    thumbnail_settings = {}
    if create_summary_image:
        thumbnail_settings["thumbnail_sizes"] = list(thumbnail_sizes)
        thumbnail_settings["projection_axis"] = projection_axis_value
        thumbnail_settings["interpolator"] = interpolator_value

    logger.info(f"Starting {analysis_type} analysis on {root_dir}")
    
    # Perform the analysis
    if analysis_type == "per_file":
        df = inspect_files(
            root_dir,
            max_processes,
            disable_tqdm,
            imageIO=image_io_value,
            meta_data_info=dict(zip(metadata_keys_headings, metadata_keys)),
            external_programs_info=dict(
                zip(external_applications_headings, external_applications)
            ),
            thumbnail_settings=thumbnail_settings,
        )
    elif analysis_type == "per_series":
        # For per_series analysis, filter the additional series tags
        # Series and study instance UIDs are always included
        filtered_tags = list(
            set([t.lower() for t in additional_series_tags])
            - {"0020|000e", "0020|000d"}
        )
        
        df = inspect_series(
            root_dir,
            max_processes,
            disable_tqdm,
            additional_series_tags=filtered_tags,
            meta_data_info=dict(zip(metadata_keys_headings, metadata_keys)),
            thumbnail_settings=thumbnail_settings,
        )

    # Check if we have valid results
    if len(df) == 0 or len(df.columns) == 1:
        logger.error(f"No report created, no successfully read images from root directory ({root_dir})")
        sys.exit(0)

    # Create output directory if needed
    output_dir = output_file.parent
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    # Handle summary image if requested
    if create_summary_image and "thumbnail" in df.columns:
        logger.info("Creating summary image")
        faux_volume = image_list_to_faux_volume(
            df["thumbnail"].dropna().to_list(), list(tile_sizes)
        )
        summary_image_path = output_file.with_suffix("").with_suffix(".nrrd")
        sitk.WriteImage(
            faux_volume,
            str(summary_image_path.with_name(f"{summary_image_path.stem}_summary_image.nrrd")),
            useCompression=True,
        )
        df.drop("thumbnail", axis=1, inplace=True)

    # Remove problematic files if requested
    if ignore_problems:
        df.dropna(inplace=True, thresh=2)
    
    # Save the CSV output
    df.to_csv(output_file, index=False)
    logger.info(f"Results saved to {output_file}")

    # Check for duplicates
    if not ignore_problems:
        df.dropna(inplace=True, thresh=2)
    
    image_counts = df["MD5 intensity hash"].value_counts().reset_index(name="count")
    duplicates = df[
        df["MD5 intensity hash"].isin(
            image_counts[image_counts["count"] > 1]["MD5 intensity hash"]
        )
    ].sort_values(by=["MD5 intensity hash"])
    
    if not duplicates.empty:
        duplicates_file = output_file.with_name(f"{output_file.stem}_duplicates.csv")
        duplicates.to_csv(duplicates_file, index=False)
        logger.info(f"Found {len(duplicates)} duplicate images, saved to {duplicates_file}")
    
    logger.info("Analysis completed successfully")