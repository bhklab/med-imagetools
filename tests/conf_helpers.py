import shutil
import sys
from pathlib import Path
from typing import Union

import pytest

from imgtools.logging import logger  # type: ignore

####################################################################################################
# here we create some helpers for the dataset downloading

"""
from the root of the project repo, we should ensure there is a 
directory called `data` where we can download the datasets
this directory will be created if it does not exist
"""


def ensure_data_dir_exists() -> Path:
    data_dir = Path(__file__).parent.parent / "data"
    if not data_dir.exists():
        data_dir.mkdir()
    return data_dir


####################################################################################################
