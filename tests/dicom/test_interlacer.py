import pytest
import datetime
import os
import logging
from pathlib import Path

from imgtools.dicom import Interlacer
from imgtools.dicom.crawl import Crawler

@pytest.mark.skipif(
    os.getenv("TEST_DATASET_TYPE", "public").lower() == 'public',
    reason="Test uses collections in private data"
)
def test_interlacer_private(medimage_by_collection, caplog) -> None:
    """
    test interlacer on private test data
    """

    test_collections = [
        "Head-Neck-PET-CT",
        "HNSCC"
    ]

    # Get the first collection
    for collection, series_list in medimage_by_collection.items():
        if collection in test_collections:
            crawler = Crawler(
                dicom_dir=Path(series_list[0].get('Path')).parent.parent,
                n_jobs=5,
                force=False,
            )
            crawler.crawl()
            interlacer = Interlacer(crawler.index)

            match collection:
                case "Head-Neck-PET-CT":
                    query = "CT,PT,RTSTRUCT" 
                    expected_sample_count = 6
                case "HNSCC":
                    query = "CT,RTSTRUCT"
                    expected_sample_count = 2

            samples = interlacer.query(query)
            assert len(samples) == expected_sample_count, \
                f"Expected {expected_sample_count} samples, but got {len(samples)} for collection {collection} with query '{query}'"

@pytest.mark.skipif(
    os.getenv("TEST_DATASET_TYPE", "public").lower() == 'private',
    reason="Test uses collections in public data"
)
def test_interlacer_public(medimage_by_collection, caplog) -> None:
    """
    test interlacer on public test data
    """

    test_collections = [
        "Vestibular-Schwannoma-SEG",
        "LIDC-IDRI",
    ]

    # Get the first collection
    for collection, series_list in medimage_by_collection.items():
        if collection in test_collections:
            crawler = Crawler(
                dicom_dir=Path(series_list[0].get('Path')).parent.parent,
                n_jobs=5,
                force=False,
            )
            crawler.crawl()
            interlacer = Interlacer(crawler.index)

            match collection:
                case "Vestibular-Schwannoma-SEG":
                    query = "MR,RTSTRUCT"
                    expected_sample_count = 4
                case "LIDC-IDRI":
                    query = "CT,SEG"
                    expected_sample_count = 4

            samples = interlacer.query(query)
            assert len(samples) == expected_sample_count, \
                f"Expected {expected_sample_count} samples, but got {len(samples)} for collection {collection} with query '{query}'"

def test_interlacer_visualize(medimage_by_collection, caplog) -> None:
    """
    test interlacer visualization
    """    

    for collection, series_list in medimage_by_collection.items():
        crawler = Crawler(
                dicom_dir=Path(series_list[0].get('Path')).parent.parent,
                n_jobs=5,
                force=False,
        )
        crawler.crawl()
        interlacer = Interlacer(crawler.index)

        viz_path = Path(series_list[0].get('Path')).parent.parent / collection / "interlacer.html"
        interlacer.visualize_forest(viz_path)

        assert viz_path.exists()

        break