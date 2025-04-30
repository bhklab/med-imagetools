from __future__ import annotations

import asyncio
import functools
import logging
import os
import tarfile
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, List, Optional, Pattern

from rich import print  # noqa
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from imgtools.utils.optional_import import (  # noqa
    OptionalImportError,
    optional_import,
)

aiohttp, has_aiohttp = optional_import("aiohttp")

# create a single console for all progress bars and logging
console = Console(force_terminal=True, stderr=True)
# setup logger with rich handler
logger = logging.getLogger("imgtools_datasets")
logger.setLevel(logging.INFO)
rich_handler = RichHandler(console=console, rich_tracebacks=True)
logger.handlers = []
logger.addHandler(rich_handler)

# Use optional_import instead of try/except
github, has_github = optional_import("github")

from github import Github
from github.Repository import Repository  # type: ignore # noqa

if TYPE_CHECKING:
    from pathlib import Path


class AssetStatus(str, Enum):
    EXISTS = "Exists"
    DOWNLOADING = "Downloading"
    DOWNLOADED = "Downloaded"
    EXTRACTING = "Extracting"
    DONE = "Done"
    SKIPPED = "Skipped"
    FAILED = "Failed"


@dataclass
class GitHubReleaseAsset:
    """
    Represents an asset in a GitHub release.

    Attributes
    ----------
    name : str
        Name of the asset (e.g., 'dataset.zip').
    label : str
        Label of the asset (e.g., '4D-Lung' if the name is '4D-Lung.tar.gz').
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
    label: str
    url: str
    browser_download_url: str
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
    task_id: TaskID,
    timeout_seconds: int = 300,
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
    task_id : TaskID
        The task ID for the progress bar.
    timeout_seconds : int, optional
        The timeout for the download in seconds, by default 3600.

    Returns
    -------
    Path
        The path to the downloaded file.
    """
    # Create a temporary file path with .tmp suffix
    temp_file_path = file_path.with_suffix(file_path.suffix + ".tmp")
    headers = {
        "Accept": "application/octet-stream",
    }
    if token := os.environ.get("GITHUB_TOKEN", os.environ.get("GH_TOKEN")):
        headers["Authorization"] = f"bearer {token}"

    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    max_retries = 3
    retry_delay = 5  # seconds

    async with aiohttp.ClientSession(
        timeout=timeout, raise_for_status=True
    ) as session:
        for attempt in range(max_retries):
            try:
                async with session.get(
                    download_link, headers=headers
                ) as response:
                    total = int(response.headers.get("content-length", 0))
                    progress.update(task_id, total=total)
                    with temp_file_path.open("wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            progress.update(task_id, advance=len(chunk))
                break  # If successful, break out of the retry loop
            except (
                asyncio.TimeoutError,
                aiohttp.ClientResponseError,
                aiohttp.ClientConnectionError,
            ) as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. Retrying in {retry_delay} seconds..."
                    )
                    await asyncio.sleep(retry_delay)  # Wait before retrying
                else:
                    logger.error(
                        f"Max retries reached. Error downloading {file_path.name}: {str(e)}"
                    )
                    # Clean up the temporary file if it exists
                    if temp_file_path.exists():
                        temp_file_path.unlink(missing_ok=True)
                    raise

    # Rename the temporary file to the final file path
    if temp_file_path.exists():
        temp_file_path.rename(file_path)

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
    github: Github = field(init=False, repr=False)
    repo: Repository = field(init=False, repr=False)
    _latest_release: GitHubRelease | None = field(
        default=None, init=False, repr=False
    )
    downloaded_paths: List[Path] = field(
        default_factory=list, init=False, repr=False
    )
    progress: Progress = field(
        default_factory=Progress, init=False, repr=False
    )

    asset_status: dict[str, AssetStatus] = field(
        default_factory=dict, init=False, repr=False
    )
    token: Optional[str] = field(
        default=None,
        init=True,
        repr=False,
    )

    # github parameters
    timeout = 300

    def __post_init__(self) -> None:
        # if user provides a token, use it
        # otherwise, use the token from the environment
        token = self.token or os.environ.get(
            "GITHUB_TOKEN", os.environ.get("GH_TOKEN")
        )
        if token:
            logger.info("Using GH token")
            self.github = Github(token, timeout=self.timeout)
        else:
            logger.info("No GH token found")
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
                # derive the label by removing all extensions
                label=asset.name.split(".")[0],  # noqa
                url=asset.url,
                browser_download_url=asset.browser_download_url,
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

    @property
    def latest_release(self) -> GitHubRelease:
        if self._latest_release is None:
            self._latest_release = self.get_release("latest")
        return self._latest_release

    def get_latest_release(self) -> GitHubRelease:
        """Fetches the latest release details from the repository."""
        return self.latest_release

    @property
    def datasets(self) -> List[GitHubReleaseAsset]:
        return self.latest_release.assets

    @property
    def dataset_names(self) -> List[str]:
        return [asset.label for asset in self.datasets]

    # Status format mapping for progress display
    STATUS_FORMATS: dict[AssetStatus, tuple[str, str]] = field(
        default_factory=lambda: {
            AssetStatus.EXISTS: ("green", "✅ [EXISTS     ]"),
            AssetStatus.DOWNLOADING: ("cyan", "⬇️ [DOWNLOADING]"),
            AssetStatus.DOWNLOADED: ("yellow", "📦 [DOWNLOADED ]"),
            AssetStatus.EXTRACTING: ("yellow", "📦 [EXTRACTING ]"),
            AssetStatus.DONE: ("green", "✅ [DONE       ]"),
            AssetStatus.SKIPPED: ("magenta", "⏭️ [SKIPPED    ]"),
            AssetStatus.FAILED: ("red", "❌ [FAILED     ]"),
        },
        init=False,
        repr=False,
    )

    def _update_progress(
        self,
        progress: Progress,
        task_id: TaskID,
        asset_name: str,
        completed: int = 0,
    ) -> None:
        """Update progress bar with appropriate formatting based on asset status"""
        status = self.asset_status.get(asset_name)
        if status in self.STATUS_FORMATS:
            color, emoji = self.STATUS_FORMATS[status]
            description = f"[{color}]{asset_name} {emoji} "
            progress.update(
                task_id, description=description, completed=completed
            )

    async def _process_asset(
        self,
        asset: GitHubReleaseAsset,
        dest: Path,
        progress: Progress,
        task_map: dict[str, TaskID],
    ) -> Optional[Path]:
        # this whole function can PROBABLY be cleaned up a lot lool
        targz: Path = dest / asset.name

        if asset.name.endswith(".tar.gz"):
            # remove the '.tar.gz' suffix to get the directory name
            extracted_path: Path = targz.with_suffix("").with_suffix("")
        else:
            extracted_path = dest / asset.label

        task_id: TaskID = task_map[asset.name]

        if extracted_path.exists():
            self.asset_status[asset.name] = AssetStatus.SKIPPED
            self._update_progress(progress, task_id, asset.name, completed=1)
            return extracted_path
        elif targz.exists():
            self.asset_status[asset.name] = AssetStatus.EXISTS
            self._update_progress(progress, task_id, asset.name, completed=1)
        else:
            # download the asset

            self.asset_status[asset.name] = AssetStatus.DOWNLOADING
            self._update_progress(progress, task_id, asset.name)

            try:
                p = await download_dataset(asset.url, targz, progress, task_id)
                assert p.exists() and str(p) == str(targz), (
                    f"Downloaded file {p} does not match expected path {targz}"
                )
                self.asset_status[asset.name] = AssetStatus.DOWNLOADED
                self._update_progress(
                    progress, task_id, asset.name, completed=1
                )
            except aiohttp.ClientResponseError as e:  # pragma: no cover
                self.asset_status[asset.name] = AssetStatus.FAILED
                self._update_progress(
                    progress, task_id, asset.name, completed=1
                )
                logger.error(
                    f"Error downloading {asset.name}. Skipping extraction. Error: {str(e)}"
                )
                raise e

        self.asset_status[asset.name] = AssetStatus.EXTRACTING
        self._update_progress(progress, task_id, asset.name)

        # extracting is a blocking operation, so we need to run it in a thread
        # pool
        def extract(path: Path, extract_path: Path) -> None:
            if tarfile.is_tarfile(path):
                with tarfile.open(path, "r:*") as archive:
                    archive.extractall(extract_path.parent, filter="data")
            # elif zipfile.is_zipfile(path):
            #     with zipfile.ZipFile(path, "r") as archive:
            #         archive.extractall(extract_path.parent)
            else:
                self.asset_status[asset.name] = AssetStatus.SKIPPED
                logger.info(
                    f"{asset.label} is not a tar or zip file. Skipping extraction."
                )
                self._update_progress(progress, task_id, asset.name)
                return None

        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                None, functools.partial(extract, targz, extracted_path)
            )
        except Exception:  # pragma: no cover
            self.asset_status[asset.name] = AssetStatus.FAILED
            self._update_progress(progress, task_id, asset.name)
            return None

        self.asset_status[asset.name] = AssetStatus.DONE
        self._update_progress(progress, task_id, asset.name)
        return extracted_path

    def download(
        self,
        dest: Path,
        assets: Optional[List[GitHubReleaseAsset]] = None,
        exclude: Optional[List[Pattern[str]]] = None,
    ) -> List[Path]:
        if assets is None:
            if self.latest_release is None:
                raise ValueError(
                    "No release found. Please call `get_latest_release` first."
                )
            assets = self.latest_release.assets

        if exclude:
            import re

            exclude = [re.compile(f".*{name}.*") for name in exclude]
            assets = [
                asset
                for asset in assets
                if not any(p.match(asset.name) for p in exclude)
            ]

        for asset in assets:
            self.asset_status[asset.name] = AssetStatus.SKIPPED

        task_map: dict[str, TaskID] = {}
        logger.info(
            f"Downloading {len(assets)} assets from {self.repo_name}..."
        )
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}", justify="right"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            TimeElapsedColumn(),
            console=console,
            # disable progress bar in CI
            disable=os.environ.get("CI", "").lower() == "true",
        ) as progress:
            # Create tasks first
            for asset in assets:
                task_map[asset.name] = progress.add_task(
                    description=f"[white]{asset.label}", total=1
                )

            dest.mkdir(parents=True, exist_ok=True)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            extracted_paths = loop.run_until_complete(
                asyncio.gather(
                    *(
                        self._process_asset(asset, dest, progress, task_map)
                        for asset in assets
                    )
                )
            )
            loop.close()

        logger.info(
            f"Downloaded {len(assets)} assets from {self.repo_name} to {dest}"
        )

        return [p for p in extracted_paths if p is not None]
