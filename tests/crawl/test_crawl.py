from pathlib import Path
import pytest
from rich import print as rprint
import pandas as pd
from imgtools.crawler import crawl

"""
This stuff will be hard coded unfortunately, and will be tedious to adjust if
we ever make changes to the test data. but its the best we can do for now.

idea test would be 

'collection' : {
  'modality' : dict of counts,
  'references' : make sure all the references collected stay the same so we can refactor without breaking tests
}

"""


COLLECTIONS = {
	"4D-Lung": {
		"CT": 70,
		"RTSTRUCT": 50,
	},
	"Adrenal-ACC-Ki67-Seg": {
		"CT": 6,
		"SEG": 2,
	},
	"CC-Tumor-Heterogeneity": {
		"CT": 6,
		"PT": 6,
		"MR": 48,
		"RTSTRUCT": 6,
		"REG": 33,
	},
	"LIDC-IDRI": {
		"CT": 3,
		"SEG": 15,
		"SR": 15,
		"CR": 1,
	},
	"Mediastinal-Lymph-Node-SEG": {
		"CT": 2,
		"SEG": 2,
	},
	"NSCLC-Radiomics": {
		"CT": 2,
		"RTSTRUCT": 2,
		"SEG": 2,
	},
	"NSCLC_Radiogenomics": {
		"PT": 6,
		"CT": 6,
		"SEG": 3,
	},
	"Prostate-Anatomical-Edge-Cases": {
		"CT": 2,
		"RTSTRUCT": 2,
	},
	"QIN-PROSTATE-Repeatability": {
		"MR": 20,
		"SEG": 12,
		"SR": 12,
	},
	"Soft-tissue-Sarcoma": {
		"MR": 8,
		"CT": 2,
		"PT": 2,
		"RTSTRUCT": 12,
	},
	"Vestibular-Schwannoma-SEG": {
		"MR": 4,
		"RTPLAN": 4,
		"RTSTRUCT": 4,
		"RTDOSE": 4,
	},
  "Head-Neck-PET-CT": {
    "CT": 2,
    "PT": 2,
    "RTSTRUCT": 4,
    "RTPLAN": 2,
    "RTDOSE": 2,
  }
}


@pytest.mark.parametrize("dataset_key", [
  "Adrenal-ACC-Ki67-Seg",
  "LIDC-IDRI",
  "Mediastinal-Lymph-Node-SEG",
  # "NSCLC-Radiomics",
  # "NSCLC_Radiogenomics",
  "Prostate-Anatomical-Edge-Cases",
  # "QIN-PROSTATE-Repeatability",
  "Soft-tissue-Sarcoma",
  "Vestibular-Schwannoma-SEG",
  "Head-Neck-PET-CT"
])
def test_shared_datadir_datasets(data_paths, dataset_key) -> None:
  """
  Test that each dataset key exists in the copied shared dataset directory.
  """
  rprint(f"Checking dataset: {dataset_key}")
  assert dataset_key in data_paths, f"Dataset key {dataset_key} not found"
  assert data_paths[dataset_key].exists(), f"Dataset {dataset_key} not found"


  db = crawl(
    top=data_paths[dataset_key],
    n_jobs=1,
  )

  assert isinstance(db, dict), "Expected a dictionary output"
  assert len(db) > 0, "Expected non-empty dictionary output"

  top_dir = Path(data_paths[dataset_key])
  imgtools_dir = top_dir.parent / ".imgtools"
  crawl_path = imgtools_dir / f"imgtools_{dataset_key}.csv"

  assert crawl_path.exists(), f"Expected crawl file {crawl_path} not found"
  assert crawl_path.with_suffix(".json").exists()  , f"Expected crawl file {crawl_path.with_suffix('.json')} not found"

  # read in the csv, get the "modality" column, use collections counter to count the unique values
  # verify that the counts match the expected counts within the COLLECTIONS dictionary

  df = pd.read_csv(crawl_path, index_col=0, dtype={"modality": str})
  modality_counts = df["modality"].value_counts()

  for modality, count in modality_counts.items():
    assert modality in COLLECTIONS[dataset_key], f"Modality {modality} not found in COLLECTIONS"
    assert count == COLLECTIONS[dataset_key][modality], f"Expected {COLLECTIONS[dataset_key][modality]} {modality} files, found {count}"

