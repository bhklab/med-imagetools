# Interlacer Module

The **Interlacer** module builds and searches a tree-like structure made from DICOM series using metadata links. This makes it easier to group, explore, and work with medical imaging data. It replaces the old `DataGraph` module from `med-imagetools 1.0`.

---

## Overview

This module turns DICOM series into a set of trees (a forest), using metadata to connect related series. This helps users follow the relationships between series — for example, linking a CT scan to its RTSTRUCT and RTDOSE — and makes it easier to run queries or group series by type.

---

## Main Classes

### `SeriesNode`

Represents one DICOM series and its connections to other related series. Each node holds:

- Basic metadata like `SeriesInstanceUID` and `Modality`
- Links to parent and child series

---

### `Branch`

Represents a single path through the tree, showing an ordered set of modalities. This is useful for queries.

---

### `GroupBy` *(Enum)*

Used to pick how series should be grouped when building the forest. Options are:

- `ReferencedSeriesUID` – Link series using metadata references  
- `StudyInstanceUID` – Group everything in the same study  
- `PatientID` – Group all series from the same patient

!!! note  

    Right now, only `ReferencedSeriesUID` is supported.

---

### `Interlacer`

This is the main class. It handles:

- **Building the forest** from a list of DICOM series  
- **Running queries** to find certain modality paths (like "CT,RTSTRUCT")  
- **Visualizing the forest** to see how series are connected

---

## Usage Example

```python
from pathlib import Path
from rich import print  # noqa

from imgtools.dicom.crawl import (
    CrawlerSettings,
    Crawler,
)
from imgtools.dicom.interlacer import Interlacer

# Define path to DICOM directory
dicom_dir = Path("data")

# Create crawler settings and crawler instance
crawler_settings = CrawlerSettings(
    dicom_dir=dicom_dir,
    n_jobs=12,
    force=False
)
crawler = Crawler(crawler_settings)
interlacer = Interlacer(crawler.index)

# Visualize the constructed forest
interlacer.print_tree(dicom_dir)
interlacer.visualize_forest(dicom_dir / "interlacer.html")

# Query modality chains (e.g., CT followed by RTSTRUCT)
query = "CT,RTSTRUCT"
samples = interlacer.query(query)
```

## Example Output

![Unstructured Data](../../images/unstructured.png){: style="height:125%;"}

![Structured Data](../../images/structured.png){: style="height:125%;"}
