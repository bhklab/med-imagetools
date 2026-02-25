import os

import click
from pathlib import Path

from imgtools.loggers import logger

cpu_count: int | None = os.cpu_count()
DEFAULT_WORKERS: int = cpu_count - 2 if cpu_count is not None else 1


@click.command(no_args_is_help=True)
@click.option(
    "--nifti-dir",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to the image directory (NIfTI, NRRD, etc.).",
)
@click.option(
    "--scan-name-pattern",
    type=str,
    required=True,
    help="Template for scan paths, e.g. '{PatientID}/{Modality}.nii.gz'. Use {placeholders} for path segments.",
)
@click.option(
    "--mask-name-pattern",
    type=str,
    default=None,
    help="Optional template for mask paths, e.g. '{PatientID}/segmentations/{ROI}.nii.gz'.",
)
@click.option(
    "--extension",
    "-e",
    "extensions",
    type=str,
    multiple=True,
    default=None,
    help="File extension(s) to search (e.g. .nii.gz, .nii, .nrrd). Can be repeated. Default: .nii.gz, .nii.",
)
@click.option(
    "--metadata-path",
    type=click.Path(exists=True, path_type=Path),
    multiple=True,
    default=None,
    help="Path(s) to CSV or JSON to merge into the index. Requires --metadata-join-col.",
)
@click.option(
    "--metadata-join-col",
    type=str,
    default=None,
    help="Column that must appear as a {placeholder} in the patterns and in each metadata file. Required when --metadata-path is set.",
)
@click.option(
    "--deep",
    is_flag=True,
    default=False,
    help="Read each image and compute fingerprint (slower). If not set, only path and match metadata are collected.",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to the output directory. If not specified, a '.imgtools' directory is created in the parent of the image directory.",
)
@click.option(
    "--dataset-name",
    type=str,
    default=None,
    help="Name of the dataset. If not specified, the name of the image directory will be used.",
)
@click.option(
    "--n-jobs",
    type=int,
    default=DEFAULT_WORKERS,
    help="Number of jobs to use for parallel processing.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Force overwrite existing cache and index.",
)
@click.help_option(
    "-h",
    "--help",
)
def niftiindex(
    nifti_dir: Path,
    scan_name_pattern: str,
    mask_name_pattern: str | None,
    extensions: tuple[str, ...] | None,
    metadata_path: tuple[Path, ...] | None,
    metadata_join_col: str | None,
    output_dir: Path | None,
    dataset_name: str | None,
    deep: bool,
    n_jobs: int,
    force: bool,
) -> None:
    """Crawl image directory and create an index of scan/mask pairs.

    Works with NIfTI (.nii, .nii.gz), NRRD (.nrrd), and other formats supported by
    SimpleITK. Discovers files matching the scan (and optional mask) path patterns,
    extracts metadata, and writes an index CSV and cache under the output directory.
    By default, results are saved in a '.imgtools' folder next to the image directory.
    """
    from imgtools.nifti.crawl import Crawler
    from imgtools.dicom.crawl import CrawlerOutputDirError

    if metadata_path and not metadata_join_col:
        raise click.UsageError("--metadata-join-col is required when --metadata-path is set.")

    crawler = Crawler(
        nifti_dir=nifti_dir,
        scan_name_pattern=scan_name_pattern,
        mask_name_pattern=mask_name_pattern,
        extensions=list(extensions) if extensions else [".nii.gz", ".nii"],
        metadata_path=list(metadata_path) if metadata_path else None,
        metadata_join_col=metadata_join_col,
        output_dir=output_dir,
        dataset_name=dataset_name,
        deep=deep,
        n_jobs=n_jobs,
        force=force,
    )
    try:
        crawler.crawl()
    except CrawlerOutputDirError as e:
        logger.exception("Output directory error")
        # exit with a non-zero status code
        raise click.ClickException(f"Output directory error: {e}") from e
    except Exception as e:
        logger.exception("Unknown Crawling Error has occurred")
        # exit with a non-zero status code
        raise click.ClickException(f"Crawling failed") from e
    else:
        logger.info("Crawling completed successfully.")
        logger.info("Crawl results saved to %s", crawler.output_dir)


if __name__ == "__main__":
    niftiindex()
