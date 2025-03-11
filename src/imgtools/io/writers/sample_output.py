from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from imgtools.io.base_classes import BaseOutput
from imgtools.io.writers import ExistingFileMode, NIFTIWriter, AbstractBaseWriter, HDF5Writer
from imgtools.utils import sanitize_file_name
from imgtools.modalities import Scan, Dose, Segmentation, PET 

CONTEXT_KEYS = [
    'ContrastBolusStopTime', 
    'PixelSpacing', 
    'CTDIvol', 
    'AcquisitionTime', 
    'NumberOfTemporalPositions', 
    'ExtractedNumberOfROIs', 
    'SliceThickness', 
    'ImagePositionPatient', 
    'PatientPosition', 
    'RescaleSlope', 
    'PatientID', 
    'ConvolutionKernel', 
    'DiffusionGradientDirectionSequence', 
    'ReconstructionMethod', 
    'AcquisitionDate', 
    'BodyPartExamined', 
    'DiffusionBMatrixSequence', 
    'PixelBandwidth', 
    'StationName', 
    'TotalCollimationWidth', 
    'ParallelAcquisitionTechnique', 
    'TableMotion', 
    'Exposure', 
    'ContrastBolusIngredientConcentration', 
    'DataCollectionDiameter', 
    'InstitutionName', 
    'TemporalResolution', 
    'SingleCollimationWidth', 
    'FrameReferenceTime', 
    'ProtocolName', 
    'ExposureTime', 
    'AcquisitionContrast', 
    'Modality', 
    'ReconstructionAlgorithm', 
    'RescaleIntercept', 
    'TransmitCoilName', 
    'ReconstructionFieldOfView', 
    'NumberOfAverages', 
    'NumberOfSlices', 
    'ScanOptions', 
    'EchoTrainLength', 
    'ParallelReductionFactorOutOfPlane', 
    'ManufacturerModelName', 
    'DetectorType', 
    'RepetitionTime', 
    'TableSpeed', 
    'SeriesInstanceUID', 
    'ContrastBolusStartTime', 
    'AcquisitionType', 
    'RescaleType', 
    'SpiralPitchFactor', 
    'SequenceName', 
    'MagneticFieldStrength', 
    'ImagingFrequency', 
    'SequenceVariant', 
    'ContrastBolusAgent', 
    'DataCollectionCenterPatient', 
    'DetectorConfiguration', 
    'KVP', 
    'EchoTime', 
    'PercentSampling', 
    'Manufacturer', 
    'ContrastFlowRate', 
    'DeviceSerialNumber', 
    'ReferencedSeriesInstanceUID', 
    'StudyInstanceUID', 
    'ScanProgressionDirection', 
    'ContrastFlowDuration', 
    'ImageOrientationPatient', 
    'ContrastBolusVolume', 
    'ReconstructionDiameter', 
    'ContrastBolusIngredient', 
    'ParallelReductionFactorInPlane', 
    'SpacingBetweenSlices', 
    'AcquisitionDateTime', 
    'SoftwareVersions', 
    'XRayTubeCurrent', 
    'OriginalNumberOfROIs', 
    'GantryDetectorTilt', 
    'ScanType', 
    'InversionTime', 
    'PercentPhaseFieldOfView', 
    'ExposureModulationType', 
    'ScanningSequence', 
    'ReconstructionTargetCenterPatient', 
    'FlipAngle',
    'RadiopharmaceuticalCodeSequence', 
    'Radiopharmaceutical', 
    'DecayCorrected', 
    'AcquisitionTerminationCondition', 
    'DecayCorrection', 
    'AcquisitionStartCondition', 
    'RadiopharmaceuticalStopDateTime', 
    'EnergyWindowUpperLimit', 
    'ActualFrameDuration', 
    'RadiopharmaceuticalStartDateTime', 
    'EnergyWindowLowerLimit', 
    'RadiopharmaceuticalRoute', 
    'SUVType', 
    'RadiopharmaceuticalVolume', 
    'RadionuclideHalfLife', 
    'RadionuclidePositronFraction', 
    'ScatterCorrectionMethod', 
    'RadionuclideTotalDose', 
    'DeadTimeCorrectionFlag', 
    'RadiopharmaceuticalStartTime', 
    'DecayFactor', 
    'TimeSliceVector', 
    'FrameTime', 
    'RadiopharmaceuticalSpecificActivity', 
    'CoincidenceWindowWidth', 
    'AttenuationCorrectionMethod'
]

@dataclass
class SampleOutput(BaseOutput):
    """
    Class for writing Sample data.

    Attributes
    ----------
    context_keys : list[str]
        All possible keys that should be included in the index file.
    root_directory : Path
        Root directory for output files.
    filename_format : str
        Format string for output filenames.
    create_dirs : bool
        Whether to create directories if they don't exist.
    existing_file_mode : ExistingFileMode
        How to handle existing files.
    sanitize_filenames : bool
        Whether to sanitize filenames.
    writer_type : str
        Type of writer to use.
    """
    root_directory: Path
    context_keys: list[str] | None = field(default=None)
    filename_format: str = field(
        default="{SampleID}/{Modality}_Series-{SeriesInstanceUID}/{ImageID}.nii.gz"
    )
    create_dirs: bool = field(default=True)
    existing_file_mode: ExistingFileMode = field(default=ExistingFileMode.SKIP)
    sanitize_filenames: bool = field(default=True)
    writer_type: str = field(default="nifti")

    @property
    def writer(self) -> AbstractBaseWriter:
        match self.writer_type:
            case "nifti":
                return NIFTIWriter
            case "hdf5":
                return HDF5Writer
            case _:
                raise ValueError(f"Unsupported writer type: {self.writer_type}")
    
    def __post_init__(self) -> None:
        self.context_keys = self.context_keys or CONTEXT_KEYS
        print(self.context_keys)
        self._writer = self.writer(
            root_directory=self.root_directory,
            filename_format=self.filename_format,
            create_dirs=self.create_dirs,
            existing_file_mode=self.existing_file_mode,
            sanitize_filenames=self.sanitize_filenames,
        )
        context = {k: "" for k in self._writer.pattern_resolver.keys}
        context.update({k: "" for k in self.context_keys})
        self._writer.set_context(**context)
        super().__init__(self._writer)

    def __call__(
            self, 
            sample: list[Scan | Dose | Segmentation | PET], 
            sample_idx: int,
            **kwargs: Any) -> None:
        """Write output data.

        Parameters
        ----------
        sample : list[Scan | Dose | Segmentation | PET]
            The sample data to be written.
        sample_idx : int
            The sample idx to be used in the SampleID field.
        **kwargs : Any
            Keyword arguments for the writing process.
        """
        SampleID = f'{sample[0].metadata["PatientID"]}_{sample_idx:03}'
        for item in sample:
            if isinstance(item, Segmentation):
                for name, label in item.roi_indices.items():
                        roi_seg = item[label]
                        self._writer.save(
                            roi_seg,
                            ImageID=f"{sanitize_file_name(name)}",
                            SampleID=SampleID,
                            **item.metadata,
                            **kwargs,
                        )      
            
            else:    
                self._writer.save(
                    item,
                    ImageID=item.metadata["Modality"],
                    SampleID=SampleID,
                    **item.metadata,
                    **kwargs,
                )

if __name__ == "__main__":
    from rich import print  # noqa
    from imgtools.dicom.crawl import CrawlerSettings, Crawler
    from imgtools.dicom.interlacer import Interlacer
    from imgtools.io.loaders import SampleInput
    from imgtools.transforms import Transformer, Resample

    crawler_settings = CrawlerSettings(
        dicom_dir=Path("data"),
        n_jobs=12,
        force=False
    )

    crawler = Crawler.from_settings(crawler_settings)

    interlacer = Interlacer(crawler.db_csv)
    interlacer.visualize_forest()
    samples = interlacer.query("CT,SEG")

    input = SampleInput(crawler.db_json)
    transform = Transformer(
        [Resample(1)]
    )
    output = SampleOutput(root_directory=".imgtools/data/output", writer_type="nifti")

    for sample_idx, sample in enumerate(samples, start=1):
        output(
            input(sample),
            sample_idx=sample_idx
        )


