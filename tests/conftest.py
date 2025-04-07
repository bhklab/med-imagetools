from pathlib import Path
import pytest
from filelock import FileLock
from enum import Enum
import os
import logging
import pandas as pd
import json
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

METADATA_CACHE_FILE = LOCKFILE.with_suffix(".json")
# TEST_ACCESS_TYPE
class TestAccessType(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"

TEST_DATASET_TYPE = TestAccessType(
    os.environ.get("TEST_DATASET_TYPE", "public").lower()
)

@pytest.fixture(scope="session")
def medimage_test_data() -> list[dict[str, str | Path]]:
    pytest_logger.info(f"Cache directory: {DATA_DIR}")
    from imgtools.datasets.github_datasets import (
        MedImageTestData,
        logger as dataset_logger,
    )
    # prevent multiple workers from downloading simultaneously
    repo = "bhklab/med-image_test-data"
    if TEST_DATASET_TYPE == TestAccessType.PRIVATE:
        repo += "_private"

    dataset_dicts = []
    with FileLock(LOCKFILE):
        # if the metadata cache file exists, read it
        if METADATA_CACHE_FILE.exists():
            pytest_logger.info(
                f"✅ Metadata cache file exists: {METADATA_CACHE_FILE}"
            )
            with open(METADATA_CACHE_FILE, "r") as f:
                dataset_dicts = json.load(f)
            
            # convert the Path
            for d in dataset_dicts:
                d["Path"] = Path(d["Path"])
            return dataset_dicts

        manager = MedImageTestData(repo_name=repo)
        manager.download(dest=DATA_DIR)

        # try looking for a *-combined_metadata.csv file
        # in the data directory
        meta = DATA_DIR / f"{TEST_DATASET_TYPE.upper()}-combined_metadata.csv"
        metadf = pd.read_csv(meta)
        missingpaths = []
        existingpaths = []
        for row in metadf.itertuples():
            collection = str(row.Collection).replace(" ", "_")
            patient_id = str(row.PatientID)
            modality = str(row.Modality)
            series_uid = str(row.SeriesInstanceUID)
            path = DATA_DIR / collection / patient_id / f"{modality}_Series{series_uid[-8:]}"
            if not path.exists():
                missingpaths.append(path)
            else:
                existingpaths.append(path)
                dataset_dicts.append({
                    "Collection": collection,
                    "PatientID": patient_id,
                    "Modality": modality,
                    "SeriesInstanceUID": series_uid,
                    "Path": path,
                    "NumInstances": row.ImageCount,
                })
        
        missing_file = DATA_DIR / "missing_paths.txt"
        if len(missingpaths) > 0:
            pytest_logger.warning(
                f"⚠️ The following paths are missing:\n{missingpaths}"
            )
            with open(missing_file, "w") as f:
                for path in missingpaths:
                    f.write(f"{path}\n")
            pytest_logger.info(
                f"✅ The following paths exist:\n{existingpaths}"
            )
            raise FileNotFoundError(
                f"Some paths are missing. Please check {missing_file} "
                " for more details."
            )
        else:
            if missing_file.exists():
                missing_file.unlink()
                pytest_logger.info(f"✅ Deleted file: {missing_file}")
        # dump file
        with open(METADATA_CACHE_FILE, "w") as f:
            # serialize the Path object to string
            for d in dataset_dicts:
                d["Path"] = str(d["Path"])
            json.dump(dataset_dicts, f, indent=4)
            pytest_logger.info(
            f"✅ Metadata cache file created: {METADATA_CACHE_FILE}"
            )
    return dataset_dicts

@pytest.fixture(scope="session")
def dataset_type() -> str:
    """Fixture to return the dataset type."""
    return TEST_DATASET_TYPE.value

@pytest.fixture(scope="session")
def public_collections() -> list[str]:
    return  [
        "4D-Lung",
        "Adrenal-ACC-Ki67-Seg",
        "CC-Tumor-Heterogeneity",
        "ISPY2",
        "LIDC-IDRI",
        "Mediastinal-Lymph-Node-SEG",
        "NSCLC-Radiomics",
        "NSCLC_Radiogenomics",
        "Prostate-Anatomical-Edge-Cases",
        "QIN-PROSTATE-Repeatability",
        "Soft-tissue-Sarcoma",
        "Vestibular-Schwannoma-SEG"
    ]

@pytest.fixture(scope="session")
def private_collections() -> list[str]:
    return [
        "HNSCC",
        "HNSCC-3DCT-RT",
        "Head-Neck-PET-CT",
        "QIN-HEADNECK",
        "RADCURE",
        "TCGA-HNSC",
        "HEAD-NECK-RADIOMICS-HN1"
    ]

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