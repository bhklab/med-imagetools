import logging
import shutil
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("mkdocs")

# show log name in log messages
logger.setLevel(logging.INFO)


def on_pre_build(config: Dict[str, Any]) -> None:
    """
    MkDocs hook to copy assets directory from the root project to the docs directory
    during build process.

    This allows markdown files to reference images using paths like `assets/image.png`
    while keeping the original assets in the root directory.

    Parameters
    ----------
    config : Dict[str, Any]
        The MkDocs configuration dictionary
    """
    # Get the logger from the config

    # Define source and destination paths
    project_root = Path(config["docs_dir"]).parent
    source_assets = project_root / "assets"
    destination_assets = Path(config["docs_dir"]) / "assets"

    # Make sure destination exists
    destination_assets.mkdir(parents=True, exist_ok=True)

    # Copy all files from source assets to destination
    if source_assets.exists():
        logger.info(
            f"Copying assets from {source_assets} to {destination_assets}"
        )

        # Remove existing destination files to avoid stale assets
        if destination_assets.exists():
            shutil.rmtree(destination_assets)

        # Copy the directory
        shutil.copytree(source_assets, destination_assets)

        logger.info("Assets successfully copied")
    else:
        logger.warning(f"Assets directory {source_assets} does not exist")


def on_post_build(config: Dict[str, Any]) -> None:
    """
    MkDocs hook to remove the copied assets directory from the docs directory
    after the build process is complete.

    Parameters
    ----------
    config : Dict[str, Any]
        The MkDocs configuration dictionary
    """
    # Get the logger from the config

    # Define the path to the copied assets directory
    destination_assets = Path(config["docs_dir"]) / "assets"

    # Remove the copied assets directory if it exists
    if destination_assets.exists():
        logger.info(f"Removing copied assets directory {destination_assets}")
        shutil.rmtree(destination_assets)
        logger.info("Assets successfully removed")
    else:
        logger.warning(
            f"Copied assets directory {destination_assets} does not exist"
        )
