import pathlib
from typing import Dict, List
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from pydicom.dataset import Dataset

from imgtools.modules.datagraph import (
    DataGraph,
)  # Replace `your_module` with the actual module name


@pytest.fixture
def 