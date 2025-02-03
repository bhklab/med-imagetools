"""
This code is for testing functioning of different modalities
"""

import os
import pathlib

import pydicom
import pytest
import SimpleITK as sitk

from imgtools.io import read_dicom_auto
from imgtools.ops import StructureSetToSegmentation


@pytest.mark.parametrize('modalities', ['CT', 'RTSTRUCT', 'RTDOSE', 'PT'])
def test_modalities(
    modalities, modalities_path
) -> None:  # modalities_path is a fixture defined in conftest.py
    path = modalities_path
    img = read_dicom_auto(path['CT']).image
    if modalities != 'RTSTRUCT':
        # Checks for dimensions
        dcm = pydicom.dcmread(
            pathlib.Path(path[modalities], os.listdir(path[modalities])[0]).as_posix()
        ).pixel_array
        instances = len(os.listdir(path[modalities]))
        dicom = read_dicom_auto(path[modalities])
        if modalities == 'CT':
            dicom = dicom.image
        if instances > 1:  # For comparing CT and PT modalities
            assert dcm.shape == (dicom.GetHeight(), dicom.GetWidth())
            assert instances == dicom.GetDepth()
        else:  # For comparing RTDOSE modalties
            assert dcm.shape == (dicom.GetDepth(), dicom.GetHeight(), dicom.GetWidth())
        if modalities == 'PT':
            dicom = dicom.resample_pet(img)
            assert dicom.GetSize() == img.GetSize()
        if modalities == 'RTDOSE':
            dicom = dicom.resample_dose(img)
            assert dicom.GetSize() == img.GetSize()
    else:
        struc = read_dicom_auto(path[modalities])
        make_binary_mask = StructureSetToSegmentation(
            roi_names=['GTV.?', 'LARYNX'], continuous=False
        )
        mask = make_binary_mask(struc, img, {'background': 0}, False)
        A = sitk.GetArrayFromImage(mask)
        assert len(A.shape) == 4
        assert A.shape[0:3] == (img.GetDepth(), img.GetHeight(), img.GetWidth())
