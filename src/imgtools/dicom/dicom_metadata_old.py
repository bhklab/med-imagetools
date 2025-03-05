import copy
from typing import Dict

import pydicom


def get_modality_metadata(
    dicom_data: pydicom.FileDataset, modality: str
) -> Dict[str, str]:
    keys = {
        "ALL": {
            "BodyPartExamined": "BodyPartExamined",
            "DataCollectionDiameter": "DataCollectionDiameter",
            "NumberofSlices": "NumberofSlices",
            "SliceThickness": "SliceThickness",
            "ScanType": "ScanType",
            "ScanProgressionDirection": "ScanProgressionDirection",
            "PatientPosition": "PatientPosition",
            "ContrastType": "ContrastBolusAgent",
            "Manufacturer": "Manufacturer",
            "ScanOptions": "ScanOptions",
            "RescaleType": "RescaleType",
            "RescaleSlope": "RescaleSlope",
            "ManufacturerModelName": "ManufacturerModelName",
        },
        "CT": {
            "KVP": "KVP",
            "XRayTubeCurrent": "XRayTubeCurrent",
            "ScanOptions": "ScanOptions",
            "ReconstructionAlgorithm": "ReconstructionAlgorithm",
            "ContrastFlowRate": "ContrastFlowRate",
            "ContrastFlowDuration": "ContrastFlowDuration",
            "ContrastType": "ContrastBolusAgent",
            "ReconstructionMethod": "ReconstructionMethod",
            "ReconstructionDiameter": "ReconstructionDiameter",
            "ConvolutionKernel": "ConvolutionKernel",
        },
        "MR": [
            "AcquisitionTime",
            "AcquisitionContrast",
            "AcquisitionType",
            "RepetitionTime",
            "EchoTime",
            "ImagingFrequency",
            "MagneticFieldStrength",
            "SequenceName",
        ],
        "PT": [
            "RescaleType",
            "RescaleSlope",
            "RadionuclideTotalDose",
            "RadionuclideHalfLife",
        ],
    }
    metadata: Dict[str, str] = (
        {} if modality == "ALL" else all_modalities_metadata(dicom_data)
    )
    # populating metadata
    if modality == "RTSTRUCT":
        if hasattr(dicom_data, "StructureSetROISequence"):
            metadata["numROIs"] = str(len(dicom_data.StructureSetROISequence))
    elif modality in keys:
        keys_mod = keys[modality]
        if isinstance(keys_mod, dict):
            for k in keys_mod:
                if hasattr(dicom_data, keys_mod[k]):
                    metadata[k] = getattr(dicom_data, keys_mod[k])
        elif isinstance(keys_mod, list):
            for k in keys_mod:
                if hasattr(dicom_data, k):
                    metadata[k] = getattr(dicom_data, k)
        else:
            errmsg = f"Invalid keys for modality '{modality}'."
            raise ValueError(errmsg)

    return metadata


def all_modalities_metadata(
    dicom_data: pydicom.dataset.FileDataset,
) -> Dict[str, str]:
    metadata = get_modality_metadata(dicom_data, "ALL")

    if hasattr(dicom_data, "PixelSpacing") and hasattr(
        dicom_data, "SliceThickness"
    ):
        pixel_size = copy.copy(dicom_data.PixelSpacing)
        pixel_size.append(dicom_data.SliceThickness)
        metadata["PixelSize"] = str(tuple(pixel_size))

    return metadata
