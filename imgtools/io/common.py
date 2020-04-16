import os
import glob
import re
from typing import Optional
from collections import namedtuple
from itertools import chain

import numpy as np
import pandas as pd
import SimpleITK as sitk
from pydicom import dcmread
from pydicom.misc import is_dicom

from ..utils import image_to_array



def find_dicom_paths(root_path: str, yield_directories: bool = False) -> str:
    """Find DICOM file paths in the specified root directory file tree.

    Parameters
    ----------
    root_path
        Path to the root directory specifying the file hierarchy.

    yield_directories, optional
        Whether to yield paths to directories containing DICOM files
        or separately to each file (default).


    Yields
    ------
    The paths to DICOM files or DICOM-containing directories (if
    `yield_directories` is True).

    """
    # TODO add some filtering options
    for root, dirs, files in os.walk(root_path):
        if yield_directories:
            if any((is_dicom(os.path.join(root, f)) for f in files)):
                yield root
        else:
            for f in files:
                fpath = os.path.join(root, f)
                if is_dicom(fpath):
                    yield fpath
