'''
This code is for testing functioning of different modalities 
'''


import os
from posixpath import dirname
import shutil
import warnings
from multiprocessing import cpu_count

import numpy as np
import SimpleITK as sitk
import pytest
import pydicom

from imgtools.io import read_dicom_auto
from imgtools.ops import StructureSetToSegmentation, ImageAutoOutput, Resample
from imgtools.pipeline import Pipeline

@pytest.fixture
def modalities_path():
    path = {}
    path["CT"] = "../examples/data_test/patient_1/08-27-1885-CA ORL FDG TEP POS TX-94629/3.000000-Merged-06362"
    path["RTSTRUCT"] = "../examples/data_test/patient_1/08-27-1885-OrophCB.0OrophCBTRTID derived StudyInstanceUID.-94629/Pinnacle POI-41418"
    path["RTDOSE"] = "../examples/data_test/patient_1/08-27-1885-OrophCB.0OrophCBTRTID derived StudyInstanceUID.-94629/11376"
    path["PT"] = "../examples/data_test/patient_1/08-27-1885-CA ORL FDG TEP POS TX-94629/532790.000000-LOR-RAMLA-44600"
    return path

@pytest.mark.parametrize("modalities", ["CT", "RTSTRUCT","RTDOSE","PT"])
def test_modalities(modalities,modalities_path):
    path = modalities_path
    if modalities!="RTSTRUCT":
        #Checks for dimensions
        img = read_dicom_auto(path["CT"])
        dcm = pydicom.dcmread(os.path.join(path[modalities],os.listdir(path[modalities])[0])).pixel_array
        instances = len(os.listdir(path[modalities]))
        dicom = read_dicom_auto(path[modalities])
        if instances>1: #For comparing CT and PT modalities
            assert dcm.shape == (dicom.GetHeight(),dicom.GetWidth())
            assert instances == dicom.GetDepth()
        else: #For comparing RTDOSE modalties
            assert dcm.shape == (dicom.GetDepth(),dicom.GetHeight(),dicom.GetWidth())
        if modalities=="PT":
            dicom = dicom.resample_pet(img)
            assert dicom.GetSize()==img.GetSize()
        if modalities=="RTDOSE":
            dicom = dicom.resample_dose(img)
            assert dicom.GetSize()==img.GetSize()
    else:
        img = read_dicom_auto(path["CT"])
        struc = read_dicom_auto(path[modalities])
        make_binary_mask = StructureSetToSegmentation(roi_names=[], continuous=False)
        mask = make_binary_mask(struc, img)
        A = sitk.GetArrayFromImage(mask)
        assert len(A.shape)==4
        assert A.shape[0:3]==(img.GetDepth(),img.GetHeight(),img.GetWidth())