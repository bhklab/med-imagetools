from pathlib import Path
import pytest
from filelock import FileLock
from enum import Enum
import os
import logging
import pandas as pd
import json
from collections import defaultdict
import pytest
from typing import TypedDict
from pathlib import Path

pytest_logger = logging.getLogger("tests.fixtures")
pytest_logger.setLevel(logging.DEBUG)

pytest_logger.propagate = True  # Let pytest capture it

# TEST_ACCESS_TYPE
class TestAccessType(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"


@pytest.fixture(scope="session")
def TEST_DATASET_TYPE() -> TestAccessType:
    """Fixture for the test dataset type (public or private)."""
    return TestAccessType(
        os.environ.get("TEST_DATASET_TYPE", "public").lower()
    )

@pytest.fixture(scope="session")
def dataset_type(TEST_DATASET_TYPE) -> str:
    """Returns the current test dataset type (public or private).
    
    Provides access to the configured dataset type for tests that need
    to behave differently based on the available test data. The value
    comes from the TEST_DATASET_TYPE environment variable.
    """
    return TEST_DATASET_TYPE.value

@pytest.fixture(scope="session")
def DATA_DIR() -> Path:
    """Fixture for the data directory."""
    data_dir = Path(__file__).parent.parent / "data"
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture(scope="session")
def LOCKFILE(DATA_DIR,TEST_DATASET_TYPE) -> Path:
    """Fixture for the lockfile path."""
    return DATA_DIR / f"{TEST_DATASET_TYPE.value}-medimage_testdata.lock"

@pytest.fixture(scope="session")
def METADATA_CACHE_FILE(LOCKFILE) -> Path:
    """Fixture for the metadata cache file path."""
    return LOCKFILE.with_suffix(".json")

class MedImageDataEntry(TypedDict):
	Collection: str
	PatientID: str
	Modality: str
	SeriesInstanceUID: str
	Path: Path
	NumInstances: int

@pytest.fixture(scope="session")
def medimage_test_data(
    TEST_DATASET_TYPE,
    LOCKFILE,
    DATA_DIR,
    METADATA_CACHE_FILE,
    ) -> list[MedImageDataEntry]:
    """Provides access to medical imaging test data files.
    
    Downloads and caches standardized medical imaging test data from GitHub.
    The data is downloaded only once per session and cached for subsequent 
    access. Supports both public and private datasets based on the 
    TEST_DATASET_TYPE environment variable.

    Returns
    -------
    list[MedImageDataEntry]
        List of dictionaries containing metadata for each test data entry.
        See `MedImageDataEntry` for the structure of each entry.

    """
    pytest_logger.info(f"Cache directory: {DATA_DIR}")
    from imgtools.datasets.github_datasets import MedImageTestData

    # configure which test data type
    repo = "bhklab/med-image_test-data"
    if TEST_DATASET_TYPE == TestAccessType.PRIVATE:
        repo += "_private"

    dataset_dicts = []
    # prevent multiple workers from downloading simultaneously
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

            match TEST_DATASET_TYPE:
                case TestAccessType.PUBLIC:
                    # public data
                    path = DATA_DIR / collection / patient_id / f"{modality}_Series-{series_uid[-8:]}"
                case TestAccessType.PRIVATE: # temp until new release
                    # private data
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

###############################################################################
# Fixtures to group test data by various metadata
###############################################################################

@pytest.fixture(scope="session")
def medimage_by_collection(
    medimage_test_data: list[MedImageDataEntry],
) -> dict[str, list[MedImageDataEntry]]:
    """Groups test data by collection name.

    organizes `medimage_test_data` into a dictionary where the keys are
    collection names for easier access when testing collection-specific
    functionality.
    """
    grouped: dict[str, list[MedImageDataEntry]] = defaultdict(list)
    for entry in medimage_test_data:
        grouped[entry["Collection"]].append(entry)
    return grouped

@pytest.fixture(scope="session")
def medimage_by_modality(
	medimage_test_data: list[MedImageDataEntry],
) -> dict[str, list[MedImageDataEntry]]:
	"""Groups test data by imaging modality.

	organizes `medimage_test_data` into a dictionary where the keys are 
    modality type (e.g., CT, MRI, PET) for easier access when testing 
    modality-specific functionality.

	Parameters
	----------
	medimage_test_data : list of MedImageDataEntry
	    Test dataset metadata entries.

	Returns
	-------
	DefaultDict[str, list[MedImageDataEntry]]
	    Dictionary mapping modality to list of entries.
	"""
	grouped: dict[str, list[MedImageDataEntry]] = defaultdict(list)
	for entry in medimage_test_data:
		grouped[entry["Modality"]].append(entry)
	return grouped

@pytest.fixture(scope="session")
def medimage_by_seriesUID(
    medimage_test_data: list[MedImageDataEntry],
) -> dict[str, MedImageDataEntry]:
    """Groups test data by SeriesInstanceUID.

    organizes `medimage_test_data` into a dictionary where the keys are
    SeriesInstanceUID for easier access when testing series-specific
    functionality.
    """
    return {
        entry["SeriesInstanceUID"]: entry
        for entry in medimage_test_data
    }

@pytest.fixture(scope="session")
def public_collections() -> list[str]:
    """Public collections available 
    """
    return  [
        "4D-Lung",
        "Adrenal-ACC-Ki67-Seg",
        "CC-Tumor-Heterogeneity",
        'CPTAC-CCRCC',
        'Pancreatic-CT-CBCT-SEG',
        'Colorectal-Liver-Metastases',
        'NSCLC-Radiomics-Interobserver1',
        'Pediatric-CT-SEG',
        'CT_Lymph_Nodes',
        'ReMIND',
        'Spine-Mets-CT-SEG',
        'CPTAC-PDA',
        'C4KC-KiTS',
        'CPTAC-UCEC',
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
    """Returns the list of private test data collections.
    
    Provides a standardized list of all available private medical imaging 
    collections that can be used in tests when working with private test data.
    Access to these collections may require special permissions.
    """
    return [
        "HNSCC",
        "HNSCC-3DCT-RT",
        "Head-Neck-PET-CT",
        "QIN-HEADNECK",
        "RADCURE",
        "TCGA-HNSC",
        "HEAD-NECK-RADIOMICS-HN1"
    ]

@pytest.fixture(scope="session")
def available_collections(dataset_type: str, public_collections: list[str], private_collections: list[str]) -> list[str]:
    """Returns the list of available collections based on the dataset type.
    
    Combines public and private collections based on the TEST_DATASET_TYPE
    environment variable.
    """
    if dataset_type == TestAccessType.PUBLIC.value:
        return public_collections
    elif dataset_type == TestAccessType.PRIVATE.value:
        return private_collections
    else:
        raise ValueError(f"Unknown dataset type: {dataset_type}")

def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run completes, right before returning the exit status."""
    pytest_logger.info("✅ Pytest session finished.")