"""
The following series were identified as having the 'SpacingBetweenSlices'
tag that was negative. This would result in the issue https://github.com/SimpleITK/SimpleITK/issues/2214
that we handle in `Scan.__init__` by flipping the direction cosines.


Note: These test datasets are only available in the private test data!

-2.5
1.3.6.1.4.1.14519.5.2.1.1706.4009.694806727342184691498467273614

-3.0
1.3.6.1.4.1.14519.5.2.1.1706.4009.129364874560309565315667317504

-3.0
1.3.6.1.4.1.14519.5.2.1.5168.2407.316675519384816522302881406362

-3.0
1.3.6.1.4.1.14519.5.2.1.5168.2407.281929332789553545546044022964

-2.0
1.3.6.1.4.1.14519.5.2.1.5168.2407.699401677458889636897043276324

-3.0
1.3.6.1.4.1.14519.5.2.1.5168.2407.208685212796869587939403105195
"""
import pytest
from imgtools.coretypes.imagetypes.scan import read_dicom_scan
import os
import logging


@pytest.mark.skipif(
    os.getenv("TEST_DATASET_TYPE", "public").lower() == 'public',
    reason="Series with direction issues are not in the public test data."
)
@pytest.mark.parametrize(
    "SeriesInstanceUID",
    [
        "1.3.6.1.4.1.14519.5.2.1.1706.4009.694806727342184691498467273614",
        "1.3.6.1.4.1.14519.5.2.1.1706.4009.129364874560309565315667317504",
        "1.3.6.1.4.1.14519.5.2.1.5168.2407.316675519384816522302881406362",
        "1.3.6.1.4.1.14519.5.2.1.5168.2407.281929332789553545546044022964",
        "1.3.6.1.4.1.14519.5.2.1.5168.2407.699401677458889636897043276324",
        "1.3.6.1.4.1.14519.5.2.1.5168.2407.208685212796869587939403105195"
    ]
)
def test_sitk_direction_issue(SeriesInstanceUID, medimage_by_seriesUID, caplog) -> None:
    """
    Test that the direction cosines are flipped when the 'SpacingBetweenSlices' tag is negative.
    Also verify that the correction is properly logged.
    """
    
    # Read the DICOM series
    series = medimage_by_seriesUID[SeriesInstanceUID]
    imgtools_logger = logging.getLogger("imgtools")
    imgtools_logger.setLevel(logging.DEBUG)
    imgtools_logger.propagate = True
    caplog.set_level(logging.DEBUG, logger="imgtools")
    # Read the scan
    scan = read_dicom_scan(series['Path'], series_id=SeriesInstanceUID)

    assert float(scan.metadata['SpacingBetweenSlices']) < 0, "SpacingBetweenSlices was not negative."

    # Check that the direction cosines are flipped
    assert scan.direction.to_matrix()[2][2] > 0, "Direction cosines were not flipped correctly."

    assert any('Manually correcting the direction' in message for message in caplog.messages), "Correction was not logged."
    assert any('Scan direction corrected' in message for message in caplog.messages), "Correction was not logged."