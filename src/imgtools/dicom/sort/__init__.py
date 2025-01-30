# ruff: noqa: I001
"""
Sorting DICOM Files by Specific Tags and Patterns.

This module provides functionality to organize DICOM files into structured
directories based on customizable target patterns.

The target patterns allow metadata-driven file organization using placeholders
for DICOM tags, enabling flexible and systematic storage.

Extended Summary
----------------
Target patterns define directory structures using placeholders, such as
`%<DICOMKey>` and `{DICOMKey}`, which are resolved to their corresponding
metadata values in the DICOM file.

This approach ensures that files are
organized based on their metadata, while retaining their original basenames.
Files with identical metadata fields are placed in separate directories to
preserve unique identifiers.

Examples of target patterns:

    - `%PatientID/%StudyID/{SeriesID}/`
    - `path/to_destination/%PatientID/images/%Modality/%SeriesInstanceUID/`

**Important**: Only the directory structure is modified during the sorting
process. The basename of each file remains unchanged.

Notes
-----
The module ensures that:

1. Target patterns are resolved accurately based on the metadata in DICOM files.
2. Files are placed in ***directories*** that reflect their resolved metadata fields.
3. **Original basenames are preserved** to prevent unintended overwrites!

Examples
--------
Source file:

```
/source_dir/HN-CHUS-082/1-1.dcm
```

Target directory pattern:

```
./data/dicoms/%PatientID/Study-%StudyInstanceUID/Series-%SeriesInstanceUID/%Modality/
```

would result in the following structure for each file:

```
data/
└── dicoms/
    └── {PatientID}/
        └── Study-{StudyInstanceUID}/
            └── Series-{SeriesInstanceUID}/
                └── {Modality}/
                    └── 1-1.dcm
```

And so the ***resolved path*** for the file would be:

```
./data/dicoms/HN-CHUS-082/Study-06980/Series-67882/RTSTRUCT/1-1.dcm
```

Here, the file is relocated into the resolved directory structure:

```
./data/dicoms/HN-CHUS-082/Study-06980/Series-67882/RTSTRUCT/
```

while the basename `1-1.dcm` remains unchanged.
"""

from imgtools.dicom.sort.exceptions import (
    DICOMSortError,
    InvalidDICOMKeyError,
    InvalidPatternError,
    SorterBaseError,
)
from imgtools.dicom.sort.highlighter import TagHighlighter
from imgtools.pattern_parser.parser import PatternParser
from imgtools.dicom.sort.sort_method import FileAction, handle_file
from imgtools.dicom.sort.sorter_base import SorterBase, resolve_path
from imgtools.dicom.sort.utils import read_tags
from imgtools.dicom.sort.dicomsorter import DICOMSorter

__all__ = [
    "TagHighlighter",
    "DICOMSortError",
    "InvalidDICOMKeyError",
    "InvalidPatternError",
    "SorterBaseError",
    "PatternParser",
    "SorterBase",
    "read_tags",
    "FileAction",
    "handle_file",
    "resolve_path",
    "DICOMSorter",
]
