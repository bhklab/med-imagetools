import os
import click
import pathlib

from typing import List, Dict, Any, Tuple, Union, Optional
from pydicom import dcmread
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm
from imgtools.logging import logger
from collections import defaultdict


# Function to process each DICOM file and extract metadata
def process_dicom_file(filepath: pathlib.Path) -> Optional[Dict]:
    try:
        meta = dcmread(filepath, force=True, stop_before_pixels=True)
        return {
            "patient_id": str(meta.PatientID),
            "study_uid": str(meta.StudyInstanceUID),
            "study_description": getattr(meta, "StudyDescription", ""),
            "series_uid": str(meta.SeriesInstanceUID),
            "series_description": getattr(meta, "SeriesDescription", ""),
            "instance_uid": str(meta.SOPInstanceUID),
            "filepath": str(filepath),
            "modality": getattr(meta, "Modality", ""),
            "reference_ct": getattr(
                meta, "ReferencedSeriesSequence[0].SeriesInstanceUID", ""
            ),
            "orientation": str(getattr(meta, "ImageOrientationPatient", "")),
            "orientation_type": getattr(meta, "AnatomicalOrientationType", ""),
            "repetition_time": float(getattr(meta, "RepetitionTime", 0.0)),
            "echo_time": float(getattr(meta, "EchoTime", 0.0)),
            "scan_sequence": getattr(meta, "ScanningSequence", ""),
            "magnetic_field_strength": float(
                getattr(meta, "MagneticFieldStrength", 0.0)
            ),
            "imaged_nucleus": getattr(meta, "ImagedNucleus", ""),
        }
    except Exception as e:
        logger.error(f"Error processing file {filepath}: {e}")
        return None


# Function to process files in parallel
def process_dicom_files_in_parallel(folder: pathlib.Path, n_jobs=-1):
    dcm_files = list(folder.rglob("*.dcm"))  # Find all DICOM files in folder
    count = 0
    workers = n_jobs if n_jobs > 0 else os.cpu_count()
    metadata_list = []
    with ProcessPoolExecutor(workers) as executor:
        with tqdm(total=len(dcm_files), desc="Processing DICOM files") as pbar:
            # Process each DICOM file in parallel and collect results
            for metadata in executor.map(process_dicom_file, dcm_files):
                metadata_list.append(metadata)
                pbar.update(1)

    logger.info(f"Finished processing. Total files found: {count}")
    return metadata_list


@click.command()
@click.option(
    "--n",
    default=os.cpu_count(),
    show_default=True,
    help="Number of parallel jobs. Default is the number of available CPUs.",
)
@click.argument(
    "directory",
    type=click.Path(
        exists=True,
        path_type=pathlib.Path,
        resolve_path=True,
        file_okay=False,
    ),
)
def main(directory: pathlib.Path, n: int = -1):
    if not directory.is_dir():
        logger.error(f"Provided path '{directory}' is not a directory.")
        return

    logger.info(f"Starting DICOM processing in folder: {directory}")
    db = process_dicom_files_in_parallel(directory, n_jobs=n)


if __name__ == "__main__":
    main()
