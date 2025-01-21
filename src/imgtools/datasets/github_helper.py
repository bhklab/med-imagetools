from pathlib import Path

import requests
from github import Github


class GitHubReleaseDataset:
    """
    Class to fetch and interact with datasets from the latest GitHub release.

    Attributes
    ----------
    repo_name : str
            The full name of the GitHub repository (e.g., 'user/repo').
    token : str | None
            Optional GitHub token for authenticated requests (higher rate limits).
    """

    def __init__(self, repo_name: str, token: str | None = None):
        self.repo_name = repo_name
        self.github = Github(token) if token else Github()

    def get_latest_release(self) -> dict:
        """Fetches the latest release details from the repository."""
        repo = self.github.get_repo(self.repo_name)
        release = repo.get_latest_release()
        return {
            "tag_name": release.tag_name,
            "name": release.title,
            "assets": [
                {"name": asset.name, "url": asset.browser_download_url}
                for asset in release.get_assets()
            ],
        }

    def download_asset(self, url: str, dest: Path) -> Path:
        """
        Downloads a release asset to a specified directory.

        Parameters
        ----------
        url : str
                Asset download URL.
        dest : Path
                Destination directory where the file will be saved.

        Returns
        -------
        Path
                Path to the downloaded file.
        """
        response = requests.get(url, stream=True)
        response.raise_for_status()
        filename = url.split("/")[-1]
        filepath = dest / filename

        with open(filepath, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        return filepath


# Usage example
if __name__ == "__main__":
    repo_name = "bhklab/med-image_test-data"
    dataset_manager = GitHubReleaseDataset(repo_name)

    # Fetch latest release info
    latest_release = dataset_manager.get_latest_release()
    print(f"Latest release: {latest_release['name']} ({latest_release['tag_name']})")
    print("Assets:")
    for asset in latest_release["assets"]:
        print(f"- {asset['name']}: {asset['url']}")

    # # Download the first asset as an example
    # download_dir = Path("./downloads")
    # download_dir.mkdir(exist_ok=True)

    # first_asset = latest_release["assets"][0]
    # print(f"Downloading {first_asset['name']}...")
    # file_path = dataset_manager.download_asset(first_asset["url"], download_dir)
    # print(f"Downloaded to {file_path}")
