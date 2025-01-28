import os
import pathlib
from pathlib import Path
from typing import Generator, Tuple
from urllib import request
from zipfile import ZipFile

import pytest

from imgtools.datasets.github_helper import (
    GitHubRelease,
    MedImageTestData,
)
from imgtools.logging import logger  # type: ignore

from .conf_helpers import ensure_data_dir_exists  # type: ignore


@pytest.fixture(scope="session")
def data_dir() -> pathlib.Path:
    return ensure_data_dir_exists()


@pytest.fixture(scope="session")
def download_all_test_data(data_dir: pathlib.Path) -> dict[str, Path]:
    # Download QC dataset
    logger.info("Downloading the test dataset...")
    manager = MedImageTestData()
    latest_release: GitHubRelease = manager.get_latest_release()
    zip_dir = data_dir
    zip_dir.mkdir(parents=True, exist_ok=True)
    _ = manager.download(zip_dir, assets=latest_release.assets)
    extracted_paths = manager.extract(data_dir)
    dataset_path_mapping = {
        unzip_path.name: unzip_path for unzip_path in extracted_paths
    }
    return dataset_path_mapping


@pytest.fixture(scope="session")
def curr_path() -> str:
    return pathlib.Path(__file__).parent.parent.resolve().as_posix()


@pytest.fixture(scope="session")
def dataset_path(
    curr_path: str, data_dir: pathlib.Path
) -> Generator[Tuple[str, str, str, str], None, None]:
    # quebec_path = pathlib.Path(curr_path, "data", "Head-Neck-PET-CT")
    quebec_path = data_dir / "Head-Neck-PET-CT"

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
        os.remove(quebec_zip_path)  # noqa: PTH107
    else:
        logger.info("Data already downloaded...")

    output_path = pathlib.Path(curr_path, "tests", "temp").as_posix()
    quebec_path_str = quebec_path.as_posix()  # type: ignore

    # Dataset name
    dataset_name = os.path.basename(quebec_path)  # noqa: PTH119
    imgtools_path = pathlib.Path(os.path.dirname(quebec_path), ".imgtools")  # noqa: PTH120

    # Defining paths for autopipeline and dataset component
    crawl_path = pathlib.Path(
        imgtools_path, f"imgtools_{dataset_name}.csv"
    ).as_posix()
    edge_path = pathlib.Path(
        imgtools_path, f"imgtools_{dataset_name}_edges.csv"
    ).as_posix()
    # json_path =  pathlib.Path(imgtools_path, f"imgtools_{dataset_name}.json").as_posix()  # noqa: F841

    yield quebec_path_str, output_path, crawl_path, edge_path


@pytest.fixture(scope="session")
def modalities_path(curr_path: str) -> dict[str, str]:
    qc_path = pathlib.Path(
        curr_path, "data", "Head-Neck-PET-CT", "HN-CHUS-052"
    )
    assert qc_path.exists(), "Dataset not found"

    path = {}
    path["CT"] = pathlib.Path(
        qc_path, "08-27-1885-CA ORL FDG TEP POS TX-94629/3.000000-Merged-06362"
    ).as_posix()
    path["RTSTRUCT"] = pathlib.Path(
        qc_path,
        "08-27-1885-OrophCB.0OrophCBTRTID derived StudyInstanceUID.-94629/Pinnacle POI-41418",
    ).as_posix()
    path["RTDOSE"] = pathlib.Path(
        qc_path,
        "08-27-1885-OrophCB.0OrophCBTRTID derived StudyInstanceUID.-94629/11376",
    ).as_posix()
    path["PT"] = pathlib.Path(
        qc_path,
        "08-27-1885-CA ORL FDG TEP POS TX-94629/532790.000000-LOR-RAMLA-44600",
    ).as_posix()
    return path
