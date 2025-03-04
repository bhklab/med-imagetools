from pydicom.dataset import FileDataset

__all__ = ["MODALITY_TAGS", "extract_dicom_tags"]

# Define modality-based tag mapping
MODALITY_TAGS = {
    "ALL": {
        # Image Geometry & Size
        "BodyPartExamined",
        "DataCollectionDiameter",
        "NumberOfSlices",
        "SliceThickness",
        "PatientPosition",
        "PixelSpacing",
        "ImageOrientationPatient",
        "ImagePositionPatient",
        # Image Processing & Rescaling
        "RescaleType",
        "RescaleSlope",
        "RescaleIntercept",
        # Scanner & Manufacturer Information
        "Manufacturer",
        "ManufacturerModelName",
        "DeviceSerialNumber",
        "SoftwareVersions",
        "InstitutionName",
        "StationName",
        # Image Acquisition Parameters
        "ScanType",
        "ScanProgressionDirection",
        "ScanOptions",
        "AcquisitionDateTime",
        "AcquisitionDate",
        "AcquisitionTime",
        "ProtocolName",
    },
    "CT": {
        # Contrast & Enhancement
        "ContrastFlowDuration",
        "ContrastFlowRate",
        "ContrastBolusAgent",
        "ContrastBolusVolume",
        "ContrastBolusStartTime",
        "ContrastBolusStopTime",
        "ContrastBolusIngredient",
        "ContrastBolusIngredientConcentration",
        # X-ray Exposure & Dose
        "KVP",
        "XRayTubeCurrent",
        "ExposureTime",
        "Exposure",
        "ExposureModulationType",
        "CTDIvol",
        # Image Reconstruction & Processing
        "ReconstructionAlgorithm",
        "ReconstructionDiameter",
        "ReconstructionMethod",
        "ReconstructionTargetCenterPatient",
        "ReconstructionFieldOfView",
        "ConvolutionKernel",
        # Scan & Acquisition Parameters
        "SpiralPitchFactor",
        "SingleCollimationWidth",
        "TotalCollimationWidth",
        "TableSpeed",
        "TableMotion",
        "GantryDetectorTilt",
        "DetectorType",
        "DetectorConfiguration",
        "DataCollectionCenterPatient",
    },
    "MR": {
        # Magnetic Field & RF Properties
        "MagneticFieldStrength",
        "ImagingFrequency",
        "TransmitCoilName",
        # Sequence & Acquisition Parameters
        "SequenceName",
        "ScanningSequence",
        "SequenceVariant",
        "AcquisitionContrast",
        "AcquisitionType",
        "EchoTime",
        "RepetitionTime",
        "InversionTime",
        "EchoTrainLength",
        "NumberOfAverages",
        "FlipAngle",
        "PercentSampling",
        "PercentPhaseFieldOfView",
        "PixelBandwidth",
        "SpacingBetweenSlices",
        # Diffusion Imaging
        "DiffusionGradientDirectionSequence",
        "DiffusionBMatrixSequence",
        # Parallel Imaging & Acceleration
        "ParallelAcquisitionTechnique",
        "ParallelReductionFactorInPlane",
        "ParallelReductionFactorOutOfPlane",
        # Functional MRI (fMRI)
        "NumberOfTemporalPositions",
        "TemporalResolution",
        "FrameReferenceTime",
    },
    # Existing PT section remains unchanged
    "PT": {
        # Radiotracer & Injection Information
        "Radiopharmaceutical",
        "RadiopharmaceuticalStartTime",
        "RadionuclideTotalDose",
        "RadionuclideHalfLife",
        "RadionuclidePositronFraction",
        "RadiopharmaceuticalVolume",
        "RadiopharmaceuticalSpecificActivity",
        "RadiopharmaceuticalStartDateTime",
        "RadiopharmaceuticalStopDateTime",
        "RadiopharmaceuticalRoute",
        "RadiopharmaceuticalCodeSequence",
        # PET Image Quantification
        "DecayCorrection",
        "DecayFactor",
        "AttenuationCorrectionMethod",
        "ScatterCorrectionMethod",
        "DecayCorrected",
        "DeadTimeCorrectionFlag",
        "ReconstructionMethod",
        # SUV (Standardized Uptake Value) Calculation
        "SUVType",
        # Acquisition Timing & Dynamics
        "FrameReferenceTime",
        "FrameTime",
        "ActualFrameDuration",
        "AcquisitionStartCondition",
        "AcquisitionTerminationCondition",
        "TimeSliceVector",
        # PET Detector & Calibration
        "DetectorType",
        "CoincidenceWindowWidth",
        "EnergyWindowLowerLimit",
        "EnergyWindowUpperLimit",
    },
}


def extract_dicom_tags(
    dicom_dataset: FileDataset, modality: str | None = None
) -> dict[str, str | None]:
    """
    Extracts relevant DICOM tags based on the modality.

    Parameters
    ----------
    dicom_dataset : FileDataset
        A loaded DICOM dataset.
    modality : str | None, optional
        The modality of the DICOM dataset. If not provided, the modality will be
        extracted from the dicom file itself.

    Returns
    -------
    dict[str, str | None]
        Extracted tags and their values, if available.
    """
    # Retrieve the modality
    modality = modality or dicom_dataset.get("Modality")
    if not modality:
        errmsg = "Modality not found in DICOM dataset."
        raise ValueError(errmsg)

    # Get relevant tags: merge 'ALL' with modality-specific tags
    relevant_tags = MODALITY_TAGS["ALL"].copy()
    if modality in MODALITY_TAGS:
        relevant_tags.update(MODALITY_TAGS[modality])

    # Extract values
    return {tag: str(dicom_dataset.get(tag, None)) for tag in relevant_tags}


if __name__ == "__main__":
    from rich import print

    from imgtools.dicom import similar_tags, tag_exists

    all_tags = [v for values in MODALITY_TAGS.values() for v in values]

    # Check if all tags exist
    for tag in all_tags:
        if not tag_exists(tag):
            print(f"Tag '{tag}' does not exist.")
            print(f"\t\t[green]Similar tags: {similar_tags(tag, 3, 0.1)}\n")

    # Check if any tag exists in both ALL and modality-specific tags
    for modality, tags in MODALITY_TAGS.items():
        common_tags = set(tags).intersection(MODALITY_TAGS["ALL"])
        if common_tags:
            print(f"Common tags in '{modality}' and 'ALL': {common_tags}\n")
