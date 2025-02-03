import pytest

from pathlib import Path
import shutil
import os
import shutil
import sys
from pathlib import Path
from imgtools.logging import logger  # type: ignore
from rich import print as rprint
import pytest
def _win32_longpath(path):
    """
    Helper function to add the long path prefix for Windows, so that shutil.copytree
     won't fail while working with paths with 255+ chars.
    """
    if sys.platform == "win32":
        # The use of os.path.normpath here is necessary since "the "\\?\" prefix
        # to a path string tells the Windows APIs to disable all string parsing
        # and to send the string that follows it straight to the file system".
        # (See https://docs.microsoft.com/pt-br/windows/desktop/FileIO/naming-a-file)
        normalized = os.path.normpath(path)
        if not normalized.startswith("\\\\?\\"):
            is_unc = normalized.startswith("\\\\")
            # see https://en.wikipedia.org/wiki/Path_(computing)#Universal_Naming_Convention # noqa: E501
            if (
                is_unc
            ):  # then we need to insert an additional "UNC\" to the longpath prefix
                normalized = normalized.replace("\\\\", "\\\\?\\UNC\\")
            else:
                normalized = "\\\\?\\" + normalized
        return normalized
    else:
        return path


@pytest.fixture(scope="session")
def shared_datadir(data_paths, tmp_path_factory):
    new_paths = {}
    temp_path = tmp_path_factory.mktemp("data")
    # copy the data_paths to the new directory
    for key, value in data_paths.items():
        new_path = temp_path / key
        logger.debug(
            f"Copying {value} to {new_path}"
        )
        shutil.copytree(_win32_longpath(value), _win32_longpath(new_path), symlinks=True, dirs_exist_ok=True,)
        
        new_paths[key] = new_path 

    return new_paths

