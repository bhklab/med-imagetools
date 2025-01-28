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

    # Test extract
    download_dir: Path = tmp_path / "downloads"
    extract_dir: Path = tmp_path / "extracted"

    assert latest_release.tag_name >= "v0.13"

    strings_of_interest: List[str] = [
        "NSCLC-Radiomics",
        "NSCLC_Radiogenomics",
        "Vestibular-Schwannoma-SEG",
    ]
    chosen_assets: List[GitHubReleaseAsset] = [
        asset
        for asset in latest_release.assets
        if any(string in asset.name for string in strings_of_interest)
    ]

    med_image_test_data.download(download_dir, assets=chosen_assets)

    assert len(med_image_test_data.downloaded_paths) > 0
    for path in med_image_test_data.downloaded_paths:
        assert path.exists()
        assert path.is_file()

    extracted_paths: List[Path] = med_image_test_data.extract(extract_dir)
    assert len(extracted_paths) > 0
    for path in extracted_paths:
        assert path.exists()
        assert path.is_file() or path.is_dir()
        if path.is_file():
            assert path.suffix in [
                ".nii",
                ".nii.gz",
                ".dcm",
                ".jpg",
                ".png",
            ]  # Add other expected file types here
