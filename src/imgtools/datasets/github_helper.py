from __future__ import annotations

import tarfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import requests
from github import Github
from rich import print


@dataclass
class GitHubReleaseAsset:
    """
    Represents an asset in a GitHub release.

    Attributes
    ----------
    name : str
        Name of the asset (e.g., 'dataset.zip').
    url : str
        Direct download URL for the asset.
    content_type : str
        MIME type of the asset (e.g., 'application/zip').
    size : int
        Size of the asset in bytes.
    download_count : int
        Number of times the asset has been downloaded.
    """

    name: str
    url: str
    content_type: str
    size: int
    download_count: int


@dataclass
class GitHubRelease:
    """
    Represents a GitHub release.

    Attributes
    ----------
    tag_name : str
        The Git tag associated with the release.
    name : str
        The name of the release.
    body : str
        Release notes or description.
    html_url : str
        URL to view the release on GitHub.
    created_at : str
        ISO 8601 timestamp of release creation.
    published_at : str
        ISO 8601 timestamp of release publication.
    assets : List[GitHubReleaseAsset]
        List of assets in the release.
    """

    tag_name: str
    name: str
    body: str
    html_url: str
    created_at: str
    published_at: str
    assets: List[GitHubReleaseAsset]


@dataclass
class GitHubReleaseManager:
    """
    Class to fetch and interact with datasets from the latest GitHub release.

    Attributes
    ----------
    repo_name : str
        The full name of the GitHub repository (e.g., 'user/repo').
    token : str | None
        Optional GitHub token for authenticated requests (higher rate limits).
    """

    repo_name: str
    github: Github
    repo: Github.Repository
    latest_release: GitHubRelease | None = None

    def __init__(self, repo_name: str, token: str | None = None):
        self.repo_name = repo_name
        self.github = Github(token) if token else Github()
        self.repo = self.github.get_repo(repo_name)

    def get_latest_release(self) -> GitHubRelease:
        """Fetches the latest release details from the repository."""

        release = self.repo.get_latest_release()

        assets = [
            GitHubReleaseAsset(
                name=asset.name,
                url=asset.browser_download_url,
                content_type=asset.content_type,
                size=asset.size,
                download_count=asset.download_count,
            )
            for asset in release.get_assets()
        ]

        self.latest_release = GitHubRelease(
            tag_name=release.tag_name,
            name=release.title,
            body=release.body or "",
            html_url=release.html_url,
            created_at=release.created_at.isoformat(),
            published_at=release.published_at.isoformat(),
            assets=assets,
        )
        return self.latest_release

    def download_asset(self, asset: GitHubReleaseAsset, dest: Path) -> Path:
        """
        Downloads a release asset to a specified directory.

        Parameters
        ----------
        asset : GitHubReleaseAsset
            The asset to download.
        dest : Path
            Destination directory where the file will be saved.

        Returns
        -------
        Path
            Path to the downloaded file.
        """
        response = requests.get(asset.url, stream=True)
        response.raise_for_status()
        dest.mkdir(parents=True, exist_ok=True)
        filepath = dest / asset.name

        if filepath.exists():
            print(f"File {asset.name} already exists. Skipping download.")
            return filepath

        with open(filepath, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        return filepath


@dataclass
class MedImageTestData(GitHubReleaseManager):
    """
    Manager for downloading and extracting med-image test data from GitHub releases.
    """

    downloaded_paths: List[Path] = field(default_factory=list, init=False)

    def __init__(self):
        super().__init__("bhklab/med-image_test-data")
        self.downloaded_paths = []

    def download_release_data(self, dest: Path) -> MedImageTestData:
        """Download all assets of the latest release to the specified directory."""
        latest_release = self.get_latest_release()
        for asset in latest_release.assets:
            print(f"Downloading {asset.name}...")
            downloaded_path = self.download_asset(asset, dest)
            self.downloaded_paths.append(downloaded_path)
        return self

    def extract(self, dest: Path) -> List[Path]:
        """Extract downloaded archives to the specified directory."""
        if not self.downloaded_paths:
            raise ValueError(
                "No archives have been downloaded yet. Call `download_release_data` first."
            )

        extracted_paths = []
        for path in self.downloaded_paths:
            print(f"Extracting {path.name}...")
            if tarfile.is_tarfile(path):
                with tarfile.open(path, "r:*") as archive:
                    archive.extractall(dest, filter="data")
                    extracted_paths.extend([dest / member.name for member in archive.getmembers()])
            elif zipfile.is_zipfile(path):
                with zipfile.ZipFile(path, "r") as archive:
                    archive.extractall(dest)
                    extracted_paths.extend([dest / name for name in archive.namelist()])
            else:
                print(f"Unsupported archive format: {path.name}")
        return extracted_paths


# Usage example
if __name__ == "__main__":
    manager = MedImageTestData()

    print(manager)

    manager.get_latest_release()

    print(manager)

    download_dir = Path("./data/med-image_test-data")
    manager.download_release_data(download_dir).extract(download_dir)
