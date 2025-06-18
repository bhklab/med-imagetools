from pathlib import Path

import pytest
import sys
from imgtools.datasets.github_datasets import (
    GitHubRelease,
    MedImageTestData,
    console,
    download_dataset,
    Progress,
    AssetStatus
)
import asyncio
from unittest.mock import MagicMock, patch
from aiohttp import ClientResponseError
import os
from github import GithubException

MINIMUM_RELEASE_VERSION = "v0.23"

PYTHON_VERSION = sys.version_info
IS_PYTHON_GREATER_3_12 = (
    PYTHON_VERSION.major == 3 and PYTHON_VERSION.minor >= 12
)


def test_get_latest_release_and_extract(
    tmp_path: Path, 
) -> None:
    # Test get_latest_release
    console.quiet = True
    med_image_test_data_manager = MedImageTestData()
    latest_release: GitHubRelease = med_image_test_data_manager.get_latest_release()
    assert latest_release is not None
    assert latest_release.tag_name is not None

    # check minimum version
    assert latest_release.tag_name >= MINIMUM_RELEASE_VERSION
    
    assert latest_release.name is not None

    assert isinstance(latest_release.tag_name, str)
    assert isinstance(latest_release.name, str)
    datasets_of_interest = [
        "NSCLC-Radiomics",
    ]
    filtered_datasets = [
        dataset
        for dataset in med_image_test_data_manager.datasets
        if dataset.label in datasets_of_interest
    ]
    assert len(filtered_datasets) == len(datasets_of_interest)
    # create temp directory
    temp_dir = tmp_path / "med_image_test_data"
    temp_dir.mkdir(parents=True, exist_ok=True)
        # test download 
    paths = med_image_test_data_manager.download(
        dest =temp_dir,
        assets = filtered_datasets
    )
    assert len(paths) == len(filtered_datasets)
    # check if the paths exist
    for path in paths:
        assert path.exists()
    assert filtered_datasets[0].name in med_image_test_data_manager.asset_status

    # download again should work
    paths = med_image_test_data_manager.download(
        dest=temp_dir,
        assets=filtered_datasets
    )
    assert len(paths) == len(filtered_datasets)
    assert filtered_datasets[0].name in med_image_test_data_manager.asset_status

@pytest.mark.asyncio
async def test_download_timeout(tmp_path: Path, ) -> None:
    console.quiet = True
    file_path = tmp_path / "testfile.txt"

    mock_response = MagicMock()
    mock_response.__aenter__.side_effect = asyncio.TimeoutError

    mock_session = MagicMock()
    mock_session.get.return_value = mock_response
    mock_session.__aenter__.return_value = mock_session

    with patch("aiohttp.ClientSession", return_value=mock_session):
        progress = Progress()
        with pytest.raises(asyncio.TimeoutError):
            await download_dataset(
                "https://example.com/fake",
                file_path,
                progress,
                task_id=progress.add_task("test"),
            )
# skip if the GH_TOKEN environment variable is not set
@pytest.mark.skipif(os.environ.get("GITHUB_TOKEN") is None, reason="GH_TOKEN environment variable is not set")
@pytest.mark.skipif(not IS_PYTHON_GREATER_3_12, reason="Python version is less than 3.12")
@pytest.mark.skipif(not sys.platform == "linux", reason="Test is only for Linux")
@pytest.mark.asyncio
async def test_accessing_private(tmp_path: Path, ) -> None:
    console.quiet = True

    manager = MedImageTestData(repo_name="bhklab/med-image_test-data_private")
    original_token = os.environ.get("GITHUB_TOKEN")
    assert original_token is not None
    # temporarily set the GH_TOKEN to None
    # to test the private repo access
    # without authentication
    os.environ["GITHUB_TOKEN"] = ""

    # this should not work
    with pytest.raises(GithubException) as excinfo:
        _ = MedImageTestData("bhklab/med-image_test-data_private")

    dataset = [d for d in manager.datasets if d.label == "TCGA-HNSC"][0]
    p = Progress()

    with pytest.raises(ClientResponseError) as excinfo:
        await download_dataset(
            dataset.url,
            tmp_path / dataset.name,
            p,
            task_id=p.add_task("test"),
        )

    os.environ["GITHUB_TOKEN"] = original_token

    path = await download_dataset(
        dataset.url,
        tmp_path / dataset.name,
        p,
        task_id=p.add_task("test"),
    )

    assert path is not None

    # downloading again should not raise an error
    # unless its on Windows
    import sys
    if sys.platform == "win32":
        with pytest.raises(OSError):
            path = await download_dataset(
                dataset.url,
                tmp_path / dataset.name,
                p,
                task_id=p.add_task("test"),
            )
        # delete the existing file
        os.remove(path)
        path = await download_dataset(
            dataset.url,
            tmp_path / dataset.name,
            p,
            task_id=p.add_task("test"),
        )
    else:
        path = await download_dataset(
            dataset.url,
            tmp_path / dataset.name,
            p,
            task_id=p.add_task("test"),
        )
        assert path is not None
