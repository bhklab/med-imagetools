from typing import Dict, List

import numpy as np
import pytest


@pytest.fixture
def roi_points() -> Dict[str, List[np.ndarray]]:
    """Fixture for mock ROI points."""
    return {
        "GTV": [np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])],
        "PTV": [np.array([[2.0, 2.0, 2.0], [3.0, 3.0, 3.0]])],
        "CTV_0": [np.array([[4.0, 4.0, 4.0], [5.0, 5.0, 5.0]])],
        "CTV_1": [np.array([[6.0, 6.0, 6.0], [7.0, 7.0, 7.0]])],
        "CTV_2": [np.array([[8.0, 8.0, 8.0], [9.0, 9.0, 9.0]])],
        "ExtraROI": [np.array([[10.0, 10.0, 10.0], [11.0, 11.0, 11.0]])],
    }


@pytest.fixture
def metadata() -> Dict[str, str]:
    """Fixture for mock metadata."""
    return {"PatientName": "John Doe"}
