"""CLI for mapping CSV columns to DICOM standard keywords."""

from pathlib import Path

import click

from imgtools.dicom.dicommap import run_mapping
from imgtools.loggers import logger


@click.command("map", no_args_is_help=True)
@click.argument(
    "csv_path",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--output-mapping",
    "-o",
    "output_mapping",
    type=click.Path(path_type=Path),
    default=None,
    help="Write column → DICOM mapping to a TOML file.",
)
@click.option(
    "--output-csv",
    type=click.Path(path_type=Path),
    default=None,
    help="Write a CSV with standardized DICOM column names (mapped columns renamed).",
)
@click.option(
    "--accept-all",
    "accept_all",
    is_flag=True,
    default=False,
    help="Non-interactive: accept first suggestion for each column (when above threshold).",
)
@click.option(
    "--threshold",
    type=float,
    default=0.6,
    help="Minimum similarity for suggestions (0–1). Default 0.6.",
)
@click.option(
    "-n",
    "top_n",
    type=int,
    default=3,
    help="Number of suggestions to show per column. Default 3.",
)
@click.option(
    "--sep",
    "delimiter",
    type=str,
    default=None,
    help="CSV delimiter (default: auto-detect).",
)
@click.option(
    "--encoding",
    type=str,
    default="utf-8-sig",
    help="CSV file encoding. Default utf-8-sig.",
)
@click.help_option("-h", "--help")
def dicommap(
    csv_path: Path,
    output_mapping: Path | None,
    output_csv: Path | None,
    accept_all: bool,
    threshold: float,
    top_n: int,
    delimiter: str | None,
    encoding: str,
) -> None:
    """Map CSV column names to DICOM standard keywords.

    Reads a metadata CSV and suggests DICOM keyword mappings for each column
    (fuzzy matching). In interactive mode you accept, reject, or skip each
    suggestion. Use --accept-all to accept all suggestions above the threshold and
    write the mapping without prompts.
    """

    if not output_mapping:
        output_mapping = (csv_path.parent / f"{csv_path.stem}_mapping.toml").resolve()
        logger.info("Mapping will be saved.", path=str(output_mapping))

    run_mapping(
        csv_path,
        output_mapping=output_mapping,
        output_csv=output_csv,
        top_n=top_n,
        threshold=threshold,
        accept_all=accept_all,
        sep=delimiter,
        encoding=encoding,
    )

