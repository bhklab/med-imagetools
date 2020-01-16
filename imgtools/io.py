import SimpleITK as sitk
from pydicom import dcmread


def read_dicom_series(path):
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(path)
    reader.SetFileNames(dicom_names)
    return reader.Execute()


def read_image(path):
    return sitk.ReadImage(path)


def read_dicom_rtstruct(path):
    return pydicom.dcmread(path)

