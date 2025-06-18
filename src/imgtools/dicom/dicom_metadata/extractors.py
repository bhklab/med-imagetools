from typing import Mapping

from pydicom import Dataset

from imgtools.dicom.dicom_metadata.extractor_base import (
    ComputedField,
    ModalityMetadataExtractor,
    classproperty,
)
from imgtools.dicom.dicom_metadata.registry import register_extractor

__all__ = [
    "CTMetadataExtractor",
    "MRMetadataExtractor",
    "PTMetadataExtractor",
    "SEGMetadataExtractor",
    "RTSTRUCTMetadataExtractor",
    "RTDOSEMetadataExtractor",
    "RTPLANMetadataExtractor",
    "SRMetadataExtractor",
]


class FallbackMetadataExtractor(ModalityMetadataExtractor):
    """
    Generic fallback extractor for unsupported or uncommon DICOM modalities.

    This extractor uses only the base tags defined in the superclass and
    defines no modality-specific tags or computed fields. It allows graceful
    handling of modalities not yet explicitly supported.
    """

    @classmethod
    def modality(cls) -> str:
        return "UNKNOWN"

    @classproperty
    def modality_tags(cls) -> set[str]:
        """
        Returns an empty set since no modality-specific tags are defined.

        Returns
        -------
        set[str]
            Empty set.
        """
        return set()

    @classproperty
    def computed_fields(cls) -> Mapping[str, ComputedField]:
        """
        Returns an empty mapping since no computed fields are defined.

        Returns
        -------
        Mapping[str, ComputedField]
            Empty mapping.
        """
        return {}


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
    def modality_tags(cls) -> set[str]:
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
    def computed_fields(cls) -> Mapping[str, ComputedField]:
        """
        CT-specific computed fields.

        Returns
        -------
        Mapping[str, ComputedField]
            Mapping of field names to functions that compute values from DICOM datasets.
        """
        return {}


@register_extractor
class MRMetadataExtractor(ModalityMetadataExtractor):
    @classmethod
    def modality(cls) -> str:
        return "MR"

    @classproperty
    def modality_tags(cls) -> set[str]:
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
    def computed_fields(cls) -> Mapping[str, ComputedField]:
        """
        MR-specific computed fields.

        Returns
        -------
        Mapping[str, ComputedField]
            Mapping of field names to functions that compute values from DICOM datasets.
        """
        return {}


@register_extractor
class PTMetadataExtractor(ModalityMetadataExtractor):
    @classmethod
    def modality(cls) -> str:
        return "PT"

    @classproperty
    def modality_tags(cls) -> set[str]:
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
    def computed_fields(cls) -> Mapping[str, ComputedField]:
        """
        PET-specific computed fields.

        Returns
        -------
        Mapping[str, ComputedField]
            Mapping of field names to functions that compute values from DICOM datasets.
        """
        return {}


@register_extractor
class SEGMetadataExtractor(ModalityMetadataExtractor):
    """

    See Also
    --------
    https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.8.20.2.html

    """

    @classmethod
    def modality(cls) -> str:
        return "SEG"

    @classproperty
    def modality_tags(cls) -> set[str]:
        return {
            # DICOM-SEG tags
            # BINARY, FRACTIONAL, or LABELMAP
            # https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.8.20.2.3.html
            "SegmentationType",
            "SegmentationFractionalType",
            "MaximumFractionalValue",
        }

    @classproperty
    def computed_fields(cls) -> Mapping[str, ComputedField]:
        """
        SEG-specific computed fields.

        Each computed field is a function that takes a pydicom.Dataset as input
        and returns a computed value. The functions are defined to extract
        relevant information from the DICOM dataset.

        Returns
        -------
        Mapping[str, ComputedField]
            Mapping of field names to functions that compute values from DICOM datasets.
        """
        from imgtools.dicom.dicom_metadata.modality_utils.seg_utils import (
            get_seg_direction,
            get_seg_spacing,
            seg_reference_uids,
        )

        def get_seg_ref_series(seg: Dataset) -> str:
            """Get the reference series UID for the segmentation."""
            return seg_reference_uids(seg)[0]

        def get_seg_ref_sop_uids(seg: Dataset) -> list[str]:
            """Get the reference SOP instance UIDs for the segmentation."""
            return seg_reference_uids(seg)[1]

        def get_seg_segmentlabels(seg: Dataset) -> list[str]:
            """Get the segment labels from the segmentation."""
            return [
                desc.get("SegmentLabel", "")
                for desc in seg.get("SegmentSequence", [])
            ]

        def get_seg_descriptions(seg: Dataset) -> list[str]:
            """Get the segment descriptions from the segmentation."""
            return [
                desc.get("SegmentDescription", "")
                for desc in seg.get("SegmentSequence", [])
            ]

        return {
            # prefix with "Seg" to avoid collision sitk computed attrbutes
            "SegSpacing": lambda ds: get_seg_spacing(ds) or "",
            "SegDirection": lambda ds: get_seg_direction(ds) or "",
            "ROINames": get_seg_segmentlabels,
            "ROIDescriptions": get_seg_descriptions,
            "ReferencedSeriesUID": get_seg_ref_series,
            "ReferencedSOPUIDs": get_seg_ref_sop_uids,
        }


@register_extractor
class RTSTRUCTMetadataExtractor(ModalityMetadataExtractor):
    """
    Metadata extractor for RTSTRUCT modality DICOM datasets.

    This class uses computed fields to extract ROI metadata and reference UIDs.
    """

    @classmethod
    def modality(cls) -> str:
        return "RTSTRUCT"

    @classproperty
    def modality_tags(cls) -> set[str]:
        """
        RTSTRUCT-specific direct tags (generally minimal).

        Returns
        -------
        set[str]
            A set of directly accessible RTSTRUCT tag names.
        """
        return {
            "StructureSetLabel",
            "StructureSetName",
            "StructureSetDate",
            "StructureSetTime",
        }

    @classproperty
    def computed_fields(cls) -> Mapping[str, ComputedField]:
        """
        RTSTRUCT-specific computed fields.

        Returns
        -------
        Mapping[str, ComputedField]
            Field names mapped to functions that extract computed values.
        """

        from imgtools.dicom.dicom_metadata.modality_utils.rtstruct_utils import (
            extract_roi_names,
            rtstruct_reference_uids,
        )

        return {
            "ReferencedSeriesUID": lambda ds: rtstruct_reference_uids(ds)[0],
            "ReferencedSOPUIDs": lambda ds: rtstruct_reference_uids(ds)[1],
            "ROINames": extract_roi_names,
            "NumROIs": lambda ds: len(extract_roi_names(ds)),
        }


@register_extractor
class RTDOSEMetadataExtractor(ModalityMetadataExtractor):
    """
    Metadata extractor for RTDOSE modality DICOM datasets.

    Extracts direct and computed reference UIDs from dose DICOM files.
    """

    @classmethod
    def modality(cls) -> str:
        return "RTDOSE"

    @classproperty
    def modality_tags(cls) -> set[str]:
        return {
            "DoseType",
            "DoseUnits",
            "DoseSummationType",
            "DoseGridScaling",
        }

    @classproperty
    def computed_fields(cls) -> Mapping[str, ComputedField]:
        from imgtools.dicom.dicom_metadata.modality_utils.rtdose_utils import (
            rtdose_reference_uids,
        )

        def get_sop_uids(ds: Dataset) -> list[str]:
            ref_pl, ref_struct, ref_series = rtdose_reference_uids(ds)
            return [ref_struct or ref_pl]

        return {
            "ReferencedSeriesUID": lambda ds: rtdose_reference_uids(ds)[2],
            "ReferencedSeriesSOPUIDs": get_sop_uids,
        }


@register_extractor
class RTPLANMetadataExtractor(ModalityMetadataExtractor):
    """
    Metadata extractor for RTPLAN modality DICOM datasets.

    Extracts basic DICOM tags and reference to an RTSTRUCT UID.
    """

    @classmethod
    def modality(cls) -> str:
        return "RTPLAN"

    @classproperty
    def modality_tags(cls) -> set[str]:
        return {
            "SeriesInstanceUID",
            "StudyInstanceUID",
            "RTPlanLabel",
            "RTPlanName",
            "RTPlanDate",
            "RTPlanTime",
        }

    @classproperty
    def computed_fields(cls) -> Mapping[str, ComputedField]:
        from imgtools.dicom.dicom_metadata.modality_utils.rtplan_utils import (
            rtplan_reference_uids,
        )

        return {"ReferencedSOPUIDs": lambda ds: [rtplan_reference_uids(ds)]}


@register_extractor
class SRMetadataExtractor(ModalityMetadataExtractor):
    """
    Metadata extractor for SR (Structured Report) modality DICOM datasets.

    Extracts referenced SeriesInstanceUIDs and SOPInstanceUIDs from structured reports.
    """

    @classmethod
    def modality(cls) -> str:
        return "SR"

    @classproperty
    def modality_tags(cls) -> set[str]:
        return {
            "SeriesInstanceUID",
            "StudyInstanceUID",
            "Modality",
            "Manufacturer",
            "ContentDate",
            "ContentTime",
            "SeriesDescription",
        }

    @classproperty
    def computed_fields(cls) -> Mapping[str, ComputedField]:
        from imgtools.dicom.dicom_metadata.modality_utils.sr_utils import (
            sr_reference_uids,
        )

        def get_series_uids(ds: Dataset) -> list[str]:
            series, _ = sr_reference_uids(ds)
            return list(series)

        def get_sop_uids(ds: Dataset) -> list[str]:
            _, sops = sr_reference_uids(ds)
            return list(sops)

        return {
            "ReferencedSeriesUID": get_series_uids,
            "ReferencedSOPUIDs": get_sop_uids,
        }
