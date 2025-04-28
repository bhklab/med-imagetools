# tests/unit/conftest.py

import pytest

def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Automatically mark all tests collected in this directory as 'unit' tests."""
    from rich import print
    for item in items:
        if item.fspath.dirname.endswith("unittests") or ('unittests' in item.fspath.dirname.split("/")):
            item.add_marker("unittests")