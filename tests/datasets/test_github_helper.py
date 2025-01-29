from pathlib import Path
from typing import List

import pytest

from imgtools.datasets.github_helper import (
    GitHubRelease,
    GitHubReleaseAsset,
    MedImageTestData,
)


@pytest.fixture
def med_image_test_data() -> MedImageTestData:
    manager = MedImageTestData()
    _ = manager.get_latest_release()
    return manager


def test_get_latest_release_and_extract(med_image_test_data: MedImageTestData, tmp_path: Path) -> None:
    # Test get_latest_release
    latest_release: GitHubRelease = med_image_test_data.get_latest_release()
    assert latest_release is not None
    assert latest_release.tag_name is not None
    assert latest_release.name is not None
    assert isinstance(latest_release.tag_name, str)
    assert isinstance(latest_release.name, str)

def test_downloaded_data_is_sound(download_all_test_data: dict[str, Path])-> None:
    assert len(download_all_test_data) > 5 
    datasets_of_interest = [
        "NSCLC-Radiomics",
        "NSCLC_Radiogenomics",
        "Vestibular-Schwannoma-SEG",
    ]

    assert all(
        dataset in download_all_test_data.keys() for dataset in datasets_of_interest
    )
    assert all(
        download_all_test_data[dataset].exists() for dataset in datasets_of_interest
    )
