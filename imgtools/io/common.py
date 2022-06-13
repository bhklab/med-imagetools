import os, pathlib
from typing import Dict

from pydicom.misc import is_dicom

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
    for root, _, files in os.walk(root_path):
        if yield_directories:
            if any((is_dicom(pathlib.Path(root, f).as_posix()) for f in files)):
                yield root
        else:
            for f in files:
                fpath = pathlib.Path(root, f).as_posix()
                if is_dicom(fpath):
                    yield fpath

def file_name_convention() -> Dict:
    """
    This function returns the file name taxonomy which is used by ImageAutoOutput and Dataset class
    """
    file_name_convention = {"CT": "image",
                            "MR": "image",
                            "RTDOSE_CT": "dose", 
                            "RTSTRUCT_CT": "mask_ct", 
                            "RTSTRUCT_MR": "mask_mr", 
                            "RTSTRUCT_PT": "mask_pt", 
                            "PT_CT": "pet", 
                            "PT": "pet", 
                            "RTDOSE": "dose", 
                            "RTSTRUCT": "mask"}
                            
    return file_name_convention