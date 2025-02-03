
import os
import shutil
import sys
from pathlib import Path

import pytest
from typing import Tuple


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


@pytest.fixture(scope="function")
def legacy_test_data(
    quebec_paths: Tuple[str, str, str, str],
    request: pytest.FixtureRequest,
    tmp_path: Path
) -> Tuple[str, str, str, str]:
    input_path, output_path, crawl_path, edge_path = quebec_paths

    assert Path(input_path).exists(), "Dataset not found"
    # idea here is to copy the data to a temporary directory
    # so that the tests can be run in isolation

    fixture_name = request.fspath.purebasename

    result = tmp_path / fixture_name

    shutil.copytree(_win32_longpath(input_path), _win32_longpath(result), symlinks=True, dirs_exist_ok=True)

    # remake the other paths

    crawl_path = result.parent / ".imgtools" / f"imgtools_{fixture_name}.csv"
    edge_path = result.parent / ".imgtools" / f"imgtools_{fixture_name}_edges.csv"
    output_path = result / "temp"

    output_path.mkdir(parents=True, exist_ok=True)
    crawl_path.parent.mkdir(parents=True, exist_ok=True)
    edge_path.parent.mkdir(parents=True, exist_ok=True)

    return result.as_posix(), output_path.as_posix(), crawl_path.as_posix(), edge_path.as_posix()
