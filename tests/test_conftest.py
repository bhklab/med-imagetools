import pytest
from rich import print as rprint


def test_conftest(download_all_test_data):
    rprint(download_all_test_data)
