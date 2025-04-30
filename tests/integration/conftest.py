# tests/integration/conftest.py
import pytest
from pathlib import Path

def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Automatically mark all tests collected in this directory as 'integration' tests."""
    for item in items:
        path = Path(item.fspath)
        if path.parts[-2] == "integration" or "integration" in path.parts:
            item.add_marker("integration")
