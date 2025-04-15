import pytest
from imgtools.coretypes.imagetypes.scan import read_dicom_scan
import os
import logging

def test_read_scan(medimage_by_collection, caplog) -> None:
    """
    test simple read_from
    """

    print(f'There are {len(medimage_by_collection)} collections in the test data.')

    # Get the first collection
    for collection, series_list in medimage_by_collection.items():
        print(f'First Series in collection {collection}: {series_list[0]}')
        scan = read_dicom_scan(series_list[0]['Path'], series_id=series_list[0]['SeriesInstanceUID'])

        # should be attrified, allowing dot access
        scan.metadata.ContentTime == '22:10:10' # type: ignore
        break
