from pathlib import Path
import pytest
from filelock import FileLock

import logging
pytest_logger = logging.getLogger("tests.fixtures")
pytest_logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "[%(asctime)s] [%(name)s] %(levelname)s - %(message)s"
)

pytest_logger.propagate = True  # Let pytest capture it


DATA_DIR = Path(__file__).parent.parent / "data"
if not DATA_DIR.exists():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
LOCKFILE = DATA_DIR / ".medimage_testdata.lock"


def pytest_sessionstart(session):
    """Called after the Session object has been created and before
    performing collection and entering the run test loop."""
    pytest_logger.info("🔓 Starting pytest session")
    if Path(LOCKFILE).exists():
        try:
            LOCKFILE.unlink()
            pytest_logger.info(f"✅ Deleted lockfile: {LOCKFILE}")
        except Exception as e:
            pytest_logger.warning(f"⚠️ Could not delete lockfile: {e}")

@pytest.fixture(scope="session")
def medimage_test_data() -> Path:
    pytest_logger.info(f"Cache directory: {DATA_DIR}")
    from imgtools.datasets.github_datasets import (
        MedImageTestData,
        logger as dataset_logger,
    )
    # prevent multiple workers from downloading simultaneously
    with FileLock(LOCKFILE):
        pytest_logger.info("Downloading medimage-testdata...")
        manager = MedImageTestData()
        manager.download(dest=DATA_DIR)
    return DATA_DIR


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run completes, right before returning the exit status."""
    pytest_logger.info("✅ Pytest session finished.")
    
    # Clean up the lockfile
    if Path(LOCKFILE).exists():
        try:
            LOCKFILE.unlink()
            pytest_logger.info(f"✅ Deleted lockfile: {LOCKFILE}")
        except Exception as e:
            pytest_logger.warning(f"⚠️ Could not delete lockfile: {e}")
