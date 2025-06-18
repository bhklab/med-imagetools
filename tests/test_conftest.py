from pathlib import Path
from collections import Counter
import pytest

def test_meta(
        medimage_test_data: list[dict[str, str | Path]],
        dataset_type: str, 
        public_collections: list[str],
        private_collections: list[str]
    ):
    """Test meta data."""
    assert medimage_test_data is not None

    counts = {
        key: Counter(d[key] for d in medimage_test_data)
        for key in medimage_test_data[0].keys()
    }
    collections : list[str] = []
    if dataset_type == "public":
        assert public_collections is not None
        collections.extend(public_collections)
    if dataset_type == "private":
        assert private_collections is not None
        collections.extend(private_collections)

    assert set(counts["Collection"]) == set(collections)


