import os
import pathlib
from urllib import request
from zipfile import ZipFile

import pytest
from filelock import FileLock

from imgtools.logging import logger


@pytest.fixture(scope="package")
def curr_path():
    return pathlib.Path().cwd().resolve().absolute()


@pytest.fixture(scope="session")
def prepare_dataset():
    """Prepares the dataset if not already downloaded."""
    curr_path = pathlib.Path().cwd().resolve().absolute()
    quebec_path = pathlib.Path(curr_path, "data", "Head-Neck-PET-CT").absolute()

    # when running xdist, use lockfile to prevent all processors from trying to download the dataset
    lock_path = quebec_path / ".dataset.lock"

    with FileLock(lock_path):
        logger.info(
            "Checking if the test dataset is downloaded...",
            curr_path=curr_path,
            quebec_path=quebec_path,
        )
        if not (quebec_path.exists() and len(list(quebec_path.glob("*"))) == 2):
            quebec_path.mkdir(parents=True, exist_ok=True)

            # Download QC dataset
            logger.info("Downloading the test dataset...")
            quebec_data_url = "https://github.com/bhklab/tcia_samples/blob/main/Head-Neck-PET-CT.zip?raw=true"
            quebec_zip_path = pathlib.Path(
                quebec_path, "Head-Neck-PET-CT.zip"
            ).as_posix()
            request.urlretrieve(quebec_data_url, quebec_zip_path)
            with ZipFile(quebec_zip_path, "r") as zipfile:
                zipfile.extractall(quebec_path)
            os.remove(quebec_zip_path)
        else:
            logger.info("Data already downloaded...")

    yield quebec_path

    # Delete the lock file
    if lock_path.exists():
        lock_path.unlink()


@pytest.fixture(scope="package")
def dataset_path(prepare_dataset):
    """Provides paths related to the dataset for tests."""
    curr_path = pathlib.Path().cwd().resolve().absolute()
    output_path = pathlib.Path(curr_path, "tests", "temp").as_posix()

    # Paths
    quebec_path = prepare_dataset.as_posix()
    dataset_name = os.path.basename(quebec_path)
    imgtools_path = pathlib.Path(os.path.dirname(quebec_path), ".imgtools")
    crawl_path = pathlib.Path(imgtools_path, f"imgtools_{dataset_name}.csv").as_posix()
    edge_path = pathlib.Path(
        imgtools_path, f"imgtools_{dataset_name}_edges.csv"
    ).as_posix()

    yield quebec_path, output_path, crawl_path, edge_path
