import pytest
from rich import print as rprint


def test_conftest(data_paths):
    rprint(data_paths)

