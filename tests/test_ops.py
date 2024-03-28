import os, pathlib
import pytest
import SimpleITK as sitk
import numpy as np
from imgtools.ops import *

@pytest.fixture(scope="session")
def output_path():
    curr_path = pathlib.Path(__file__).parent.parent.resolve()
    out_path = pathlib.Path(curr_path, "temp_outputs").as_posix()
    os.makedirs(out_path)
    return out_path

def blank():
    return np.zeros(100,100,100)

class TestOutput:
    @pytest.mark.parametrize("op", [NumpyOutput, HDF5Output, MetadataOutput])#, "CT,RTDOSE,PT"])
    def test_output(self, op):
        class_name = op.__class__.__name__
        saver = op(output_path, create_dirs=False)
        saver(class_name, blank)
        img = sitk.ReadImage(pathlib.Path(output_path, saver.filename_format.format(class_name)))
        assert img.GetSize == (100,100,100)
        
        
class TestTransform:
    def __init__(self):
        self.blank = np.zeros(100,100,100)
    
    @pytest.mark.parametrize("op", [NumpyOutput, HDF5Output, MetadataOutput])
    def test_transform(self, op):
        pass