import os
from pathlib import Path

import click

from imgtools.betapipeline import BetaPipeline
from imgtools.loggers import logger

# Set default number of workers
cpu_count = os.cpu_count()
DEFAULT_WORKERS = (cpu_count - 2) if cpu_count else 1

# Valid imaging modalities
VALID_MODALITIES = {"CT", "MR", "PT", "SEG", "RTSTRUCT", "RTDOSE"}


@click.command()
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
    default="CT,RTSTRUCT",
    show_default=True,
    type=str,
    help="Modalities to process (comma-separated).",
)
@click.option(
    "--spacing",
    default=(1.0, 1.0, 0.0),
    show_default=True,
    type=tuple,
    help="Spacing for resampling.",
)
@click.option(
    "--n_jobs",
    default=DEFAULT_WORKERS,
    show_default=True,
    type=int,
    help="Number of worker processes.",
)
@click.option(
    "--update_crawl",
    is_flag=True,
    default=False,
    show_default=True,
    help="Update existing crawl data.",
)
@click.option(
    "--roi_yaml_path",
    type=click.Path(file_okay=True, dir_okay=False, readable=True, path_type=Path, resolve_path=True),
    default=None,
    show_default=True,
    help="Path to ROI YAML file.",
)
@click.option(
    "--nnunet",
    is_flag=True,
    default=False,
    show_default=True,
    help="Save in nnUNet dataset format.",
)
@click.option(
    "--train_size",
    default=1.0,
    show_default=True,
    type=float,
    help="Proportion of samples for training/test in nnUNet.",
)
@click.option(
    "--random_state",
    default=42,
    show_default=True,
    type=int,
    help="Random seed for train/test split.",
)
def autopipeline(
    input_directory: Path,
    output_directory: Path,
    modalities: str,
    spacing: tuple,
    n_jobs: int,
    roi_yaml_path: Path | None,
    nnunet: bool,
    train_size: float,
    random_state: int,
    update_crawl: bool,
) -> None:
    """Run the AutoPipeline from the command line.

    \b
    INPUT_DIRECTORY: Path to the input directory.
    OUTPUT_DIRECTORY: Path to the output directory.
    """
    logger.debug("Running BetaPipeline via CLI with args: %s", locals())

    # Validate modalities
    mods = {mod.strip().upper() for mod in modalities.split(",")}
    if not mods.issubset(VALID_MODALITIES):
        bad_modalities = mods - VALID_MODALITIES
        logger.error(f"Invalid modalities: {bad_modalities}. Valid options: {VALID_MODALITIES}")
        msg = f"Invalid modalities: {bad_modalities}. Valid options: {VALID_MODALITIES}"
        raise ValueError(msg)

    # Initialize and run BetaPipeline
    pipeline = BetaPipeline(
        input_directory=input_directory,
        output_directory=output_directory,
        query=modalities,
        spacing=spacing,
        n_jobs=n_jobs,
        roi_yaml_path=roi_yaml_path,
        nnunet=nnunet,
        train_size=train_size,
        random_state=random_state,
        update_crawl=update_crawl,
    )
    pipeline.run()


if __name__ == "__main__":
    autopipeline()
