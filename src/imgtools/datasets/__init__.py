from .examples import (
    data_images as example_data,
    data_paths as example_data_paths,
)

__all__ = [
    "example_data",
    "example_data_paths",
]


def is_testdata_available() -> bool:
    try:
        from github import Github  # type: ignore # noqa
        import aiohttp  # noqa

        return True
    except ImportError:
        return False


if is_testdata_available():
    from .github_datasets import (
        GitHubRelease,
        GitHubReleaseAsset,
        MedImageTestData,
    )

    __all__ += [
        "GitHubRelease",
        "GitHubReleaseAsset",
        "MedImageTestData",
    ]
