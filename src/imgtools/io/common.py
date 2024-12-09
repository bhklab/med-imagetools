import os
import pathlib
from typing import Dict

from pydicom.misc import is_dicom
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
