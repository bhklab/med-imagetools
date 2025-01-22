from __future__ import annotations

import asyncio
import tarfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import aiohttp
from rich import print
from rich.console import Console
from rich.progress import Progress

# create a single console for all progress bars, so they don't clutter the output
console = Console()


try:
    from github import Github  # type: ignore # noqa
except ImportError as e:
    raise ImportError(
        "PyGithub is required for the test data feature of med-imagetools. "
        "Install it using 'pip install med-imagetools[test]'."
    ) from e


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

    def get_release(self, tag: Optional[str] = "latest") -> GitHubRelease:
        """
        Fetches the details of a specific release or the latest release if no tag is provided.

        Parameters
        ----------
        tag : str, optional
            The tag of the release to fetch. If 'latest', fetches the latest release.

        Returns
        -------
        GitHubRelease
            The details of the requested release.
        """
        if tag == "latest":
            release = self.repo.get_latest_release()
        else:
            release = self.repo.get_release(tag)

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

        return GitHubRelease(
            tag_name=release.tag_name,
            name=release.title,
            # body=release.body or "",
            body="",  # for now... we can add this later
            html_url=release.html_url,
            created_at=release.created_at.isoformat(),
            published_at=release.published_at.isoformat(),
            assets=assets,
        )

    def get_latest_release(self) -> GitHubRelease:
        """Fetches the latest release details from the repository."""
        self.latest_release = self.get_release("latest")
        return self.latest_release


@dataclass
class MedImageTestData(GitHubReleaseManager):
    """
    Manager for downloading and extracting med-image test data from GitHub releases.
    """

    downloaded_paths: List[Path] = field(default_factory=list, init=False)
    progress: Progress = field(default_factory=Progress, init=False)

    def __init__(self):
        super().__init__("bhklab/med-image_test-data")
        self.downloaded_paths = []
        self.get_latest_release()
        self.progress = Progress()

    @property
    def datasets(self) -> List[GitHubReleaseAsset]:
        return self.latest_release.assets

    @property
    def dataset_names(self) -> List[str]:
        return [asset.name for asset in self.datasets]

    async def _download_asset(
        self, session: aiohttp.ClientSession, asset: GitHubReleaseAsset, dest: Path
    ) -> Path:
        """
        Helper method to download a single asset asynchronously with a progress bar.

        Parameters
        ----------
        session : aiohttp.ClientSession
            The aiohttp session to use for the request.
        asset : GitHubReleaseAsset
            The asset to download.
        dest : Path
            Destination directory where the file will be saved.

        Returns
        -------
        Path
            Path to the downloaded file.
        """
        dest.mkdir(parents=True, exist_ok=True)
        filepath = dest / asset.name

        if filepath.exists():
            print(f"File {asset.name} already exists. Skipping download.")
            return filepath

        with self.progress:
            task_id = self.progress.add_task(f"Downloading {asset.name}", total=asset.size)

            async with session.get(asset.url) as response:
                response.raise_for_status()
                with open(filepath, "wb") as file:
                    while chunk := await response.content.read(8192):
                        file.write(chunk)
                        self.progress.update(task_id, advance=len(chunk))

        return filepath

    async def _download(
        self, dest: Path, assets: Optional[List[GitHubReleaseAsset]] = None
    ) -> List[Path]:
        """
        Download specified assets or all assets if none are specified.

        Parameters
        ----------
        dest : Path
            Destination directory where the files will be saved.
        assets : List[GitHubReleaseAsset], optional
            List of assets to download. If None, all assets will be downloaded.

        Returns
        -------
        List[Path]
            List of paths to the downloaded files.
        """
        if assets is None:
            assets = self.latest_release.assets

        async with aiohttp.ClientSession() as session:
            tasks = [self._download_asset(session, asset, dest) for asset in assets]
            self.downloaded_paths = await asyncio.gather(*tasks)
        return self.downloaded_paths

    def download_all(self, dest: Path) -> List[Path]:
        """
        Download all assets of the latest release synchronously.

        Parameters
        ----------
        dest : Path
            Destination directory where the files will be saved.

        Returns
        -------
        List[Path]
            List of paths to the downloaded files.
        """
        return asyncio.run(
            self._download(
                dest,
                assets=self.latest_release.assets,
            )
        )

    def download(self, dest: Path, assets: Optional[List[GitHubReleaseAsset]] = None) -> List[Path]:
        """
        Download specified assets synchronously.

        Parameters
        ----------
        dest : Path
            Destination directory where the files will be saved.
        assets : List[GitHubReleaseAsset], optional
            List of assets to download. If None, all assets will be downloaded.

        Returns
        -------
        List[Path]
            List of paths to the downloaded files.
        """
        print(f"Downloading assets to {dest}...")
        print(f"Assets: {', '.join(asset.name for asset in assets)}")
        return asyncio.run(self._download(dest, assets))

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

    old_release_tag = "v0.11"
    old_release = manager.get_release(old_release_tag)
    print(old_release)

    chosen_assets = old_release.assets[:2]

    dest_dir = Path("data")
    downloaded_files = manager.download(dest_dir, assets=chosen_assets)

    # release = manager.get_latest_release()

    # print(manager)

    # print(manager.datasets)

    # print(manager.dataset_names)

    # dest_dir = Path("data")
    # chosen_assets = manager.datasets[:2]

    # downloaded_files = manager.download(dest_dir, assets=chosen_assets)

    # print(downloaded_files)
