from typing import Mapping

from imgtools.dicom.dicom_metadata.extractor_base import (
    ComputedField,
    ModalityMetadataExtractor,
    classproperty,
)
from imgtools.dicom.dicom_metadata.registry import register_extractor


@register_extractor
class CTMetadataExtractor(ModalityMetadataExtractor):
    """
    Metadata extractor for CT modality DICOM datasets.

    This subclass defines modality-specific tags and computed fields relevant
    to CT (Computed Tomography) imaging. It extends the base metadata extractor
    with CT-specific acquisition and reconstruction parameters.
    """

    @classmethod
    def modality(cls) -> str:
        return "CT"

    @classproperty
    def modality_tags(cls) -> set[str]:  # noqa: N805
        """
        CT-specific DICOM tag names.

        Returns
        -------
        set[str]
            CT acquisition and reconstruction-related DICOM tags.
        """
        return {
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
        }

    @classproperty
    def computed_fields(cls) -> Mapping[str, ComputedField]:  # noqa: N805
        return {}


@register_extractor
class MRMetadataExtractor(ModalityMetadataExtractor):
    @classmethod
    def modality(cls) -> str:
        return "MR"

    @classproperty
    def modality_tags(cls) -> set[str]:  # noqa: N805
        return {
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
        }

    @classproperty
    def computed_fields(cls) -> Mapping[str, ComputedField]:  # noqa: N805
        return {}


@register_extractor
class PTMetadataExtractor(ModalityMetadataExtractor):
    @classmethod
    def modality(cls) -> str:
        return "PT"

    @classproperty
    def modality_tags(cls) -> set[str]:  # noqa: N805
        return {
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
        }

    @classproperty
    def computed_fields(cls) -> Mapping[str, ComputedField]:  # noqa: N805
        return {}
