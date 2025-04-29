# tests/unit/conftest.py

import pytest
from pathlib import Path

def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Automatically mark all tests collected in this directory as 'unit' tests."""
    for item in items:
        item_path = Path(str(item.fspath))
        if item_path.parts[-2] == "unittests" or "unittests" in item_path.parts:
            item.add_marker("unittests")