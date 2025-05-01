import pytest
from imgtools.coretypes.imagetypes.scan import read_dicom_scan
import datetime
import os
import logging

def test_read_scan(medimage_by_collection, caplog) -> None:
    """
    test simple read_from
    """

    print(f'There are {len(medimage_by_collection)} collections in the test data.')

    # Get the first collection
    for collection, series_list in medimage_by_collection.items():
        try:
            series_object = next(series for series in series_list if series.get('Modality') in ['CT', 'MR'])
        except StopIteration:
            pytest.skip(f"No CT or MR series found in collection {collection}")

        print(f'First Series in collection {collection}: {series_object}')
        scan = read_dicom_scan(series_object['Path'], series_id=series_object['SeriesInstanceUID'])
        #
        # should be attrified, allowing dot access
        assert isinstance(scan.metadata['ContentTime'], datetime.time)
        break
