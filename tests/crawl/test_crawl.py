from pathlib import Path
import pytest
from rich import print as rprint

from imgtools.utils import crawl

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

  top_dir = Path(data_paths[dataset_key])
  imgtools_dir = top_dir.parent / ".imgtools"
  crawl_path = imgtools_dir / f"imgtools_{dataset_key}.csv"

  assert crawl_path.exists(), f"Expected crawl file {crawl_path} not found"
  assert crawl_path.with_suffix(".json"), f"Expected crawl file {crawl_path.with_suffix('.json')} not found"