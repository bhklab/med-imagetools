import re
import time
from unittest.mock import patch

from imgtools.utils import timer


@patch("imgtools.utils.timer_utils.logger")
def test_timer_decorator(mock_logger) -> None:  # noqa: ANN001
    @timer("test_function")
    def test_function(x: int, y: int) -> int:
        time.sleep(0.1)  # Simulate work
        return x + y

    result = test_function(1, 2)

    assert result == 3  # Check if function works correctly
    mock_logger.info.assert_called_once()  # Check if logger was called
    log_message = mock_logger.info.call_args[0][0]

    assert re.match(r"test_function took \d+\.\d{4} seconds", log_message)


@patch("imgtools.utils.timer_utils.logger")
def test_timer_execution_time(mock_logger) -> None:  # noqa: ANN001
    @timer("sleep_function")
    def sleep_function() -> bool:
        time.sleep(0.1)
        return True

    sleep_function()

    log_message = mock_logger.info.call_args[0][0]
    execution_time = float(log_message.split()[-2])
    assert execution_time > 0.05  # More tolerant lower bound
    assert execution_time < 0.5   # More tolerant upper bound
