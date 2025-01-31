from __future__ import annotations

import asyncio
import concurrent.futures
import os
import shutil
import tarfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import aiohttp
from rich import print  # noqa
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

# create a single console for all progress bars, so they don't clutter the output
console = Console()

try:
    from github import Github  # type: ignore # noqa
    from github.Repository import Repository  # type: ignore # noqa
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
    body: str = field(repr=False)
    html_url: str
    created_at: str
    published_at: str
    assets: List[GitHubReleaseAsset]


async def download_dataset(
    download_link: str,
    file_path: Path,
    progress: Progress,
    timeout_seconds: int = 3600,
) -> Path:
    """
    Download a single dataset.

    Parameters
    ----------
    download_link : str
        The URL to download the dataset from.
    file_path : Path
        The path where the downloaded file will be saved.
    progress : Progress
        The progress bar to use for the download.
    timeout_seconds : int, optional
        The timeout for the download in seconds, by default 3600.

    Returns
    -------
    Path
        The path to the downloaded file.
    """
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(download_link) as response:
                total = int(response.headers.get("content-length", 0))
                task = progress.add_task(
                    f"[cyan]{file_path.name}...", total=total
                )
                with file_path.open("wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))
        except asyncio.TimeoutError:
            console.print(
                f"[bold red]Timeout while downloading "
                f"{file_path.name}. Please try again later.[/]"
            )
            raise
    return file_path


@dataclass
class MedImageTestData:
    """
    Manager for downloading and extracting med-image test data from GitHub releases.

    Attributes
    ----------
    repo_name : str
        The full name of the GitHub repository (e.g., 'user/repo').
    token : str | None
        Optional GitHub token for authenticated requests (higher rate limits).
    """

    repo_name: str = "bhklab/med-image_test-data"
    github: Github = field(init=False)
    repo: Repository = field(init=False)
    latest_release: GitHubRelease = field(init=False)
    downloaded_paths: List[Path] = field(default_factory=list, init=False)
    progress: Progress = field(
        default_factory=Progress, init=False, repr=False
    )

    # github parameters
    timeout = 300

    def __post_init__(self) -> None:
        token = os.environ.get("GITHUB_TOKEN", os.environ.get("GH_TOKEN"))
        if token:
            console.log("Using GH token")
            self.github = Github(token, timeout=self.timeout)
        else:
            console.log("No GH token found")
            self.github = Github(timeout=self.timeout)

        self.repo = self.github.get_repo(self.repo_name)
        self.get_latest_release()

    def get_release(self, tag: str = "latest") -> GitHubRelease:
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
            body=release.body or "",
            html_url=release.html_url,
            created_at=release.created_at.isoformat(),
            published_at=release.published_at.isoformat(),
            assets=assets,
        )

    def get_latest_release(self) -> GitHubRelease:
        """Fetches the latest release details from the repository."""
        self.latest_release = self.get_release("latest")
        return self.latest_release

    @property
    def datasets(self) -> List[GitHubReleaseAsset]:
        return self.latest_release.assets

    @property
    def dataset_names(self) -> List[str]:
        return [asset.name for asset in self.datasets]

    async def _download_asset(
        self,
        session: aiohttp.ClientSession,
        asset: GitHubReleaseAsset,
        dest: Path,
        progress: Progress,
        force: bool = False,
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
        progress : Progress
            The progress bar to use for the download.

        Returns
        -------
        Path
            Path to the downloaded file.
        """
        dest.mkdir(parents=True, exist_ok=True)
        filepath = dest / asset.name
        # also check for name without "tar.gz" extension
        alternate_name = filepath.with_suffix("").with_suffix("")
        if filepath.exists() or alternate_name.exists():
            console.print(
                f"File {asset.name} already exists. Skipping download."
            )
            return filepath

        return await download_dataset(asset.url, filepath, progress)

    async def _download(
        self,
        dest: Path,
        assets: List[GitHubReleaseAsset],
        progress: Progress,
        force: bool = False,
    ) -> List[Path]:
        """
        Download specified assets or all assets if none are specified.

        Parameters
        ----------
        dest : Path
            Destination directory where the files will be saved.
        assets : List[GitHubReleaseAsset], optional
            List of assets to download. If None, all assets will be downloaded.
        progress : Progress
            The progress bar to use for the download.

        Returns
        -------
        List[Path]
            List of paths to the downloaded files.
        """

        async with aiohttp.ClientSession() as session:
            tasks = [
                self._download_asset(session, asset, dest, progress, force)
                for asset in assets
            ]
            self.downloaded_paths = await asyncio.gather(*tasks)
        return self.downloaded_paths

    def download(
        self,
        dest: Path,
        assets: Optional[List[GitHubReleaseAsset]] = None,
        exclude: Optional[List[str]] = None,
        force: bool = False,
        cores: Optional[int] = None,
    ) -> List[Path]:
        """
        Download specified assets synchronously, extracts by default.

        Parameters
        ----------
        dest : Path
            Destination directory where the files will be saved.
        exclude: List[str], optional
            List of assets to exclude from download.
            Can be patterns or exact names.
        assets : List[GitHubReleaseAsset], optional
            List of assets to download. If None, all assets will be downloaded

        Returns
        -------
        List[Path]
            List of paths to the downloaded files or extracted directories.
        """
        if assets is None:
            assets = self.latest_release.assets

        if exclude:
            import re

            console.log(f"Excluding assets on patterns: {', '.join(exclude)}")
            # try matching OR finding exact names
            exclude = [re.compile(f".*{name}.*") for name in exclude]
            exclude_assets = [
                asset
                for asset in assets
                if any(pattern.match(asset.name) for pattern in exclude)
            ]
            console.log(
                f"Excluding assets: {', '.join(asset.name for asset in exclude_assets)}"
            )
            assets = [asset for asset in assets if asset not in exclude_assets]

        console.print(f"Downloading assets to {dest.absolute()}...")
        with Progress(
            TextColumn("[bold blue]{task.description}", justify="right"),
            BarColumn(),
            TaskProgressColumn(),
            DownloadColumn(),
            TimeRemainingColumn(),
            TimeElapsedColumn(),
            transient=True,
            console=console,
        ) as progress:
            _ = asyncio.run(self._download(dest, assets, progress, force))

        extracted_paths = self.extract(force=force, cores=cores)
        for tar_file in self.downloaded_paths:
            if tar_file.exists():
                console.log(f"Removing downloaded file: {tar_file}")
                tar_file.unlink()
        return extracted_paths

    def extract(
        self, force: bool = False, cores: Optional[int] = None
    ) -> List[Path]:
        """Extract downloaded archives to the specified directory in parallel.

        Parameters
        ----------
        force : bool, optional
            Whether to force extraction by removing existing directories, by default False.
        cores : int, optional
            Number of cores to use for parallel extraction, by default uses all available cores.

        Returns
        -------
        List[Path]
            List of paths to the extracted directories.
        """
        if not self.downloaded_paths:
            raise ValueError(
                "No archives have been downloaded yet. Call `download` first."
            )

        if cores is None:
            cores = os.cpu_count()

        def extract_archive(path: Path) -> List[Path]:
            extract_path = path.with_suffix("").with_suffix("")
            extracted_paths: List[Path] = []

            if extract_path.exists():
                if force:
                    console.print(
                        f"Removing existing directory {extract_path}..."
                    )
                    shutil.rmtree(extract_path)
                else:
                    console.print(
                        f"Directory {extract_path} already"
                        " exists. Skipping extraction."
                    )
                    extracted_paths.append(extract_path)
                    return extracted_paths

            console.log(f"Extracting {path.name}...")
            if tarfile.is_tarfile(path):
                with tarfile.open(path, "r:*") as archive:
                    archive.extractall(extract_path.parent, filter="data")
                    extracted_paths.append(extract_path)
            elif zipfile.is_zipfile(path):
                with zipfile.ZipFile(path, "r") as archive:
                    archive.extractall(extract_path.parent)
                    extracted_paths.append(extract_path)
            else:
                console.print(f"Unsupported archive format: {path.name}")
            return extracted_paths

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=cores
        ) as executor:
            results = list(
                executor.map(extract_archive, self.downloaded_paths)
            )

        # Flatten the list of lists
        return [item for sublist in results for item in sublist]


# Usage example
if __name__ == "__main__":  # pragma: no cover
    manager = MedImageTestData()

    print(manager)

    old_release = manager.get_latest_release()

    chosen_assets = old_release.assets[8:]

    dest_dir = Path("data")
    downloaded_files = manager.download(dest_dir, assets=chosen_assets)
    console.print(downloaded_files)
