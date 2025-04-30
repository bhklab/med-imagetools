# tests/e2e/conftest.py

import pytest
from pathlib import Path

def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Automatically mark all tests collected in this directory as 'e2e' tests."""
    for item in items:
        item_path = Path(str(item.fspath))
        if "e2e" in item_path.parts:
            item.add_marker("e2e")