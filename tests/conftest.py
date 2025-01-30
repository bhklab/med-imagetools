import os
import pathlib
from pathlib import Path
from typing import Generator, Tuple
from urllib import request
from zipfile import ZipFile
import json
import pytest
from filelock import FileLock


from imgtools.datasets.github_helper import (
    GitHubRelease,
    MedImageTestData,
)
from imgtools.logging import logger  # type: ignore

# from .conf_helpers import ensure_data_dir_exists  # type: ignore


@pytest.fixture(scope="session")
def data_dir() -> pathlib.Path:
    data_dir = Path(__file__).parent.parent / "data"
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture(scope="session")
def download_all_test_data(data_dir: pathlib.Path, worker_id: str | None) -> dict[str, Path]:  

    # idk how this works like in the pytest-xdist docs
    # leaving in case we need to use it later
    # if worker_id == "master":
    #     # following the pytest-xdist docs, we only want to download the data once

    #     manager = MedImageTestData()
    #     latest_release: GitHubRelease = manager.get_latest_release()
    #     # banned = ["4D-Lungs", "CC-Tumor-Heterogeneisty.tar"]
    #     banned = ["4D-Lung", "CC-Tumor-Heterogeneity.tar"]
    #     selected_tests = list(
    #         filter(
    #             lambda asset: not any(
    #                 asset.name.startswith(nope) for nope in banned
    #             ),
    #             latest_release.assets,
    #         )
    #     )
    #     extracted_paths = manager.download(data_dir, assets=selected_tests)
    #     dataset_path_mapping = {
    #         unzip_path.name: unzip_path for unzip_path in extracted_paths
    #     }
    #     return dataset_path_mapping

    lock_path = data_dir / "download_all_test_data"

    with FileLock(str(lock_path) + ".lock"):
        if lock_path.with_suffix(".json").exists():
            # Load existing dataset mapping if already downloaded
            logger.info("Loading pre-downloaded test dataset metadata...")
            loaded_json =  json.loads(lock_path.with_suffix(".json").read_text())
            dataset_path_mapping = {k: Path(v) for k, v in loaded_json.items()}
            return dataset_path_mapping
        # Download QC dataset
        logger.info("Downloading the test dataset...")
        manager = MedImageTestData()
        latest_release: GitHubRelease = manager.get_latest_release()
        banned = ["4D-Lung", "CC-Tumor-Heterogeneity.tar"]
        selected_tests = list(
            filter(
                lambda asset: not any(
                    asset.name.startswith(nope) for nope in banned
                ),
                latest_release.assets,
            )
        )
        extracted_paths = manager.download(data_dir, assets=selected_tests)
        dataset_path_mapping = {
            unzip_path.name: unzip_path for unzip_path in extracted_paths
        }
        # Save dataset mapping to avoid re-downloading in future runs
        lock_path.with_suffix(".json").write_text(
            json.dumps({k: str(v) for k, v in dataset_path_mapping.items()})
        )
        return dataset_path_mapping

@pytest.fixture(scope="session")
def download_old_test_data(data_dir: pathlib.Path) -> dict[str, Path]:
    """
    We have a few old tests that we want to keep around for now.
    this is mainly the quebec dataset
    """

    lock_path = data_dir / "download_old_test_data"

    with FileLock(str(lock_path) + ".lock"):
        if lock_path.with_suffix(".json").exists():
            # Load existing dataset mapping if already downloaded
            logger.info("Loading pre-downloaded old test dataset metadata...")
            loaded_json = json.loads(lock_path.with_suffix(".json").read_text())
            dataset_path_mapping = {k: Path(v) for k, v in loaded_json.items()}
            return dataset_path_mapping

        # Download QC dataset
        logger.info("Downloading the old test dataset...")
        quebec_data_path = data_dir / "Head-Neck-PET-CT"

        if not quebec_data_path.exists():
            quebec_data_url = "https://github.com/bhklab/tcia_samples/blob/main/Head-Neck-PET-CT.zip?raw=true"
            quebec_zip_path = quebec_data_path.with_suffix(".zip")

            quebec_data_path.mkdir(parents=True, exist_ok=True)
            request.urlretrieve(quebec_data_url, quebec_zip_path)
            with ZipFile(quebec_zip_path, "r") as zipfile:
                zipfile.extractall(quebec_data_path)
            quebec_zip_path.unlink()

        assert quebec_data_path.exists(), f"Quebec data not found at {quebec_data_path}"
        dataset_path_mapping = {
            "Head-Neck-PET-CT": quebec_data_path,
        }

        # Save dataset mapping to avoid re-downloading in future runs
        lock_path.with_suffix(".json").write_text(
            json.dumps({k: str(v) for k, v in dataset_path_mapping.items()})
        )
        return dataset_path_mapping


@pytest.fixture(scope="session")
def data_paths(
    download_all_test_data: dict[str, Path], download_old_test_data: dict[str, Path]
) -> dict[str, Path]:
    return {**download_all_test_data, **download_old_test_data}

####################################################################################################
# these ones are all OLD
# hopefully we can replace them with the new ones
@pytest.fixture(scope="session")
def curr_path() -> str:
    return pathlib.Path(__file__).parent.parent.resolve().as_posix()


@pytest.fixture(scope="session")
def quebec_paths(
    data_paths: dict[str, Path],  data_dir: pathlib.Path
) -> Tuple[str, str, str, str]:
    quebec_path = data_paths["Head-Neck-PET-CT"]
    assert quebec_path.exists(), "Dataset not found"

    output_path = pathlib.Path(data_dir.parent, "tests", "temp")
    quebec_path_str = quebec_path.as_posix()
    crawl_path = data_dir / ".imgtools" / "imgtools_Head-Neck-PET-CT.csv"
    edge_path = data_dir / ".imgtools" / "imgtools_Head-Neck-PET-CT_edges.csv"

    return quebec_path_str, output_path.as_posix(), crawl_path.as_posix(), edge_path.as_posix()


@pytest.fixture(scope="session")
def modalities_path(
    data_paths: dict[str, Path], 
) -> dict[str, str]:
    quebec_patientd_path = data_paths["Head-Neck-PET-CT"] / "HN-CHUS-052"

    assert quebec_patientd_path.exists(), "Dataset not found"

    path = {}
    path["CT"] = pathlib.Path(
        quebec_patientd_path, "08-27-1885-CA ORL FDG TEP POS TX-94629/3.000000-Merged-06362"
    ).as_posix()
    path["RTSTRUCT"] = pathlib.Path(
        quebec_patientd_path,
        "08-27-1885-OrophCB.0OrophCBTRTID derived StudyInstanceUID.-94629/Pinnacle POI-41418",
    ).as_posix()
    path["RTDOSE"] = pathlib.Path(
        quebec_patientd_path,
        "08-27-1885-OrophCB.0OrophCBTRTID derived StudyInstanceUID.-94629/11376",
    ).as_posix()
    path["PT"] = pathlib.Path(
        quebec_patientd_path,
        "08-27-1885-CA ORL FDG TEP POS TX-94629/532790.000000-LOR-RAMLA-44600",
    ).as_posix()
    return path
