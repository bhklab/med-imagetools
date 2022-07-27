import pydicom
from pydicom import dcmread
from typing import Dict, TypeVar, Union
import copy

T = TypeVar('T')

def all_modalities_metadata(dicom_data: Union[pydicom.dataset.FileDataset, pydicom.dicomdir.DicomDir]) -> Dict[str, T]:
    metadata = {}
    if hasattr(dicom_data, 'BodyPartExamined'):
        metadata["BodyPartExamined"] = str(dicom_data.BodyPartExamined)
    if hasattr(dicom_data, 'DataCollectionDiameter'):
        metadata["DataCollectionDiameter"] = str(dicom_data.DataCollectionDiameter)
    if hasattr(dicom_data, 'NumberofSlices'):
        metadata["NumberofSlices"] = str(dicom_data.NumberofSlices)
    # Slice Thickness is avg. slice thickness?
    if hasattr(dicom_data, 'SliceThickness'):
        metadata["SliceThickness"] = str(dicom_data.SliceThickness)
    if hasattr(dicom_data, 'ScanType'):
        metadata["ScanType"] = str(dicom_data.ScanType)
    # Scan Progression Direction is Scan Direction?
    if hasattr(dicom_data, 'ScanProgressionDirection'):
        metadata["ScanProgressionDirection"] = str(dicom_data.ScanProgressionDirection)
    if hasattr(dicom_data, 'PatientPosition'):
        metadata["PatientPosition"] = str(dicom_data.PatientPosition)
    # is this contrast type?
    if hasattr(dicom_data, 'ContrastBolusAgent'):
        metadata["ContrastType"] = str(dicom_data.ContrastBolusAgent)
    if hasattr(dicom_data, 'Manufacturer'):
        metadata["Manufacturer"] = str(dicom_data.Manufacturer)
    # Scan Plane?
    if hasattr(dicom_data, 'ScanOptions'):
        metadata["ScanOptions"] = str(dicom_data.ScanOptions)
    if hasattr(dicom_data, 'RescaleType'):
        metadata["RescaleType"] = str(dicom_data.RescaleType)
    if hasattr(dicom_data, 'RescaleSlope'):
        metadata["RescaleSlope"] = str(dicom_data.RescaleSlope)
    if hasattr(dicom_data, 'PixelSpacing') and hasattr(dicom_data, 'SliceThickness'):
        pixel_size = copy.copy(dicom_data.PixelSpacing)
        pixel_size.append(dicom_data.SliceThickness)
        metadata["PixelSize"] = str(tuple(pixel_size))
    if hasattr(dicom_data, 'ManufacturerModelName'):
        metadata["ManufacturerModelName"] = str(dicom_data.ManufacturerModelName)
    return metadata


def ct_metadata(dicom_data: Union[pydicom.dataset.FileDataset, pydicom.dicomdir.DicomDir]) -> Dict[str, T]:
    metadata = {}
    if hasattr(dicom_data, 'KVP'):
        metadata["KVP"] = str(dicom_data.KVP)
    if hasattr(dicom_data, 'XRayTubeCurrent'):
        metadata["XRayTubeCurrent"] = str(dicom_data.XRayTubeCurrent)
    if hasattr(dicom_data, 'ScanOptions'):
        metadata["ScanOptions"] = str(dicom_data.ScanOptions)
    if hasattr(dicom_data, 'ReconstructionAlgorithm'):
        metadata["ReconstructionAlgorithm"] = str(dicom_data.ReconstructionAlgorithm)
    if hasattr(dicom_data, 'ContrastFlowRate'):
        metadata["ContrastFlowRate"] = str(dicom_data.ContrastFlowRate)
    if hasattr(dicom_data, 'ContrastFlowDuration'):
        metadata["ContrastFlowDuration"] = str(dicom_data.ContrastFlowDuration)
    # is this contrast type?
    if hasattr(dicom_data, 'ContrastBolusAgent'):
        metadata["ContrastType"] = str(dicom_data.ContrastBolusAgent)
    if hasattr(dicom_data, 'ReconstructionMethod'):
        metadata["ReconstructionMethod"] = str(dicom_data.ReconstructionMethod)
    if hasattr(dicom_data, 'ReconstructionDiameter'):
        metadata["ReconstructionDiameter"] = str(dicom_data.ReconstructionDiameter)
    if hasattr(dicom_data, 'ConvolutionKernel'):
        metadata["ConvolutionKernel"] = str(dicom_data.ConvolutionKernel)
    return metadata
    


def mr_metadata(dicom_data: Union[pydicom.dataset.FileDataset, pydicom.dicomdir.DicomDir]) -> Dict[str, T]:
    metadata = {}
    if hasattr(dicom_data, 'AcquisitionTime'):
        metadata["AcquisitionTime"] = str(dicom_data.AcquisitionTime)
    if hasattr(dicom_data, 'AcquisitionContrast'):
        metadata["AcquisitionContrast"] = str(dicom_data.AcquisitionContrast)
    if hasattr(dicom_data, 'AcquisitionType'):
        metadata["AcquisitionType"] = str(dicom_data.AcquisitionType)
    if hasattr(dicom_data, 'RepetitionTime'):
        metadata["RepetitionTime"] = str(dicom_data.RepetitionTime)
    if hasattr(dicom_data, 'EchoTime'):
        metadata["EchoTime"] = str(dicom_data.EchoTime)
    if hasattr(dicom_data, 'ImagingFrequency'):
        metadata["ImagingFrequency"] = str(dicom_data.ImagingFrequency)
    if hasattr(dicom_data, 'MagneticFieldStrength'):
        metadata["MagneticFieldStrength"] = str(dicom_data.MagneticFieldStrength)
    if hasattr(dicom_data, 'SequenceName'):
        metadata["SequenceName"] = str(dicom_data.SequenceName)
    return metadata


def pet_metadata(pet: Union[pydicom.dataset.FileDataset, pydicom.dicomdir.DicomDir]) -> Dict[str, T]:
    metadata = {}
    if hasattr(pet, 'RescaleType'):
        metadata["RescaleType"] = str(pet.RescaleType)
    if hasattr(pet, 'RescaleSlope'):
        metadata["RescaleSlope"] = str(pet.RescaleSlope)
    if hasattr(pet, 'RadionuclideTotalDose'):
        metadata["RadionuclideTotalDose"] = str(pet.RadionuclideTotalDose)
    if hasattr(pet, 'RadionuclideHalfLife'):
        metadata["RadionuclideHalfLife"] = str(pet.RadionuclideHalfLife)
    return metadata


def rtstruct_metadata(rtstruct: Union[pydicom.dataset.FileDataset, pydicom.dicomdir.DicomDir]) -> Dict[str, T]:
    metadata = {}
    if hasattr(rtstruct, 'StructureSetROISequence'):
        metadata["numROIs"] = str(len(rtstruct.StructureSetROISequence))
    return metadata
