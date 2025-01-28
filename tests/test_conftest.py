import pytest
from rich import print


def test_conftest(download_all_test_data) -> None:
    print(download_all_test_data)
