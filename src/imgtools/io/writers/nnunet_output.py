"""
Module for writing Sample data in nnUNet format.

This module contains the `nnUNetOutput` class, which is responsible for writing sample data
into a format compatible with nnUNet, a widely used deep learning framework for medical image 
segmentation. The `nnUNetOutput` class manages the creation of necessary directories, file naming 
conventions, and how the data should be saved and processed for nnUNet training. It supports handling 
segmentation data, raw images, and metadata, ensuring all data is formatted properly for the nnUNet pipeline.

Key functionalities:
- Write sample data to nnUNet-compatible format.
- Handle segmentation and image data separately, including metadata.
- Validate sample data to ensure required information (like segmentation images) is present.
- Generate dataset JSON configuration and preprocessing scripts.
- Handle the creation of necessary directories and datasets for nnUNet processing.

Classes:
    nnUNetOutput: A class for writing sample data in nnUNet format.

Examples
--------
>>> import json
>>> from pathlib import Path
>>> from imgtools.dicom.crawl import Crawler, CrawlerSettings
>>> from imgtools.dicom.dicom_metadata import MODALITY_TAGS
>>> from imgtools.dicom.interlacer import Interlacer
>>> from imgtools.io import SampleInput, nnUNetOutput
>>>
>>> # Set the directory containing DICOM files
>>> dicom_dir = Path("data")
>>>
>>> # Set up the Crawler with DICOM directory and job settings
>>> crawler_settings = CrawlerSettings(
>>>     dicom_dir=dicom_dir,
>>>     n_jobs=12,
>>>     force=False
>>> )
>>>
>>> crawler = Crawler.from_settings(crawler_settings)
>>>
>>> # Create an Interlacer to visualize the data structure
>>> interlacer = Interlacer(crawler.db_csv)
>>> interlacer.visualize_forest()
>>>
>>> # Query for specific modalities (e.g., CT and RTSTRUCT)
>>> query = "CT,RTSTRUCT"
>>> samples = interlacer.query(query)
>>>
>>> # Define the ROI names for segmentation
>>> roi_names = {"GTV": "GTV.*"}
>>> input = SampleInput(crawler.db_json, roi_names=roi_names, ignore_missing_regex=True)
>>>
>>> # Set the context keys by combining modality tags
>>> context_keys = list(
>>>     set.union(*[MODALITY_TAGS["ALL"], 
>>>                 *[MODALITY_TAGS.get(modality, {}) for modality in query.split(",")]]
>>> )
>>>
>>> # Define ROI indices (mapping of ROI names to indices)
>>> roi_indices = {
>>>     name: idx+1 for idx, name in enumerate(roi_names.keys())
>>> }
>>>
>>> # Create an instance of nnUNetOutput for writing data
>>> output = nnUNetOutput(
>>>     root_directory=Path(".imgtools/data/output").resolve(), 
>>>     roi_indices=roi_indices,
>>>     dataset_name=dicom_dir.name, 
>>>     writer_type="nifti", 
>>>     context_keys=context_keys
>>> )
>>>
>>> output_metadata = []
>>> # Iterate over the samples, write output, and collect metadata
>>> for sample_id, sample in enumerate(samples, start=1):
>>>     metadata = output(
>>>         input(sample),
>>>         SampleID=f"{sample_id:03}",
>>>         SplitType="Tr",
>>>     )
>>>     output_metadata.append(metadata)
>>>
>>> # Print the metadata in JSON format
>>> print(json.dumps(output_metadata, indent=4))
"""


from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from imgtools.io.base_classes import BaseOutput
from imgtools.io.writers import (
    AbstractBaseWriter,
    ExistingFileMode,
    NIFTIWriter,
)
from imgtools.loggers import logger
from imgtools.modalities import PET, Scan, Segmentation
from imgtools.utils.nnunet import (
    generate_dataset_json,
    generate_nnunet_scripts,
    nnUNet_MODALITY_MAP,
)


@dataclass
class nnUNetOutput(BaseOutput):
    """
    Class for writing Sample data in nnUNet format.

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
    dataset_name: str
    roi_indices: dict[str, int]

    require_all_rois: bool = True

    context_keys: list[str] = field(default_factory=list)
    filename_format: str = field(
        default="{DirType}{SplitType}/{Dataset}_{SampleID}"
    )
    create_dirs: bool = field(default=True)
    existing_file_mode: ExistingFileMode = field(default=ExistingFileMode.SKIP)
    sanitize_filenames: bool = field(default=True)
    writer_type: str = field(default="nifti")

    @property
    def writer(self) -> AbstractBaseWriter:
        match self.writer_type:
            case "nifti":
                self.file_ending = ".nii.gz"
                self.filename_format += self.file_ending
                return NIFTIWriter
            case _:
                msg = f"Unsupported writer type: {self.writer_type}"
                raise ValueError(msg)
    
    def __post_init__(self) -> None:
        """Initialize the NIFTIWriter, set up directories, and configure the writer context."""

        # Create required directories
        for subdir in ["nnUNet_results", "nnUNet_preprocessed", "nnUNet_raw"]:
            (self.root_directory / subdir).mkdir(parents=True, exist_ok=True)

        # Determine the next available dataset ID
        existing_ids = {
            int(folder.name[7:10]) 
            for folder in (self.root_directory / "nnUNet_raw").glob("Dataset*") 
            if folder.name[7:10].isdigit()
        }
        self.dataset_id = min(set(range(1, 1000)) - existing_ids)

        # Update root directory to the specific dataset folder
        self.root_directory /= f"nnUNet_raw/Dataset{self.dataset_id:03d}_{self.dataset_name}"

        # Initialize the writer
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

    def _is_invalid_sample(self, sample: list[Scan | Segmentation | PET]) -> str:
        if not any(isinstance(image, Segmentation) for image in sample):
            # Usually happens when none of the roi names match
            return "No segmentation images found. Skipping sample." 
        
        if self.require_all_rois: 
            for image in sample:
                if isinstance(image, Segmentation) and image.roi_indices != self.roi_indices:
                    return  "ROI names do not match. Skipping sample."
        
        return ""

    def __call__(
        self, 
        sample: list[Scan | Segmentation | PET], 
        SampleID: str,
        **kwargs: Any) -> dict[str, Any]:  # noqa: ANN401
        """Write output data.

        Parameters
        ----------
        sample : list[Scan | Segmentation | PET]
            The data to be written.
        SampleID : str
            The sample ID.
        **kwargs : Any
            Keyword arguments for the writing process.
        """
        if (error := self._is_invalid_sample(sample)):
            return {
                "SampleID": SampleID,
                "Error": error,
                **kwargs
            }
        
        if ((num_segmentations := sum(isinstance(image, Segmentation) for image in sample)) 
            and num_segmentations > 1):
            logger.warning(
                "Multiple segmentation images found in sample. Only the first one will be used."
            )
        
        roi_names = {}
        for image in sample:
            # Only include keys that are in the writer context
            image_metadata = {k: image.metadata[k] for k in self._writer.context if k in image.metadata}

            if isinstance(image, Segmentation):
                roi_seg = image.generate_sparse_mask(new_roi_indices=self.roi_indices)
                roi_names.update(roi_seg.roi_indices)
                self._writer.save(
                    roi_seg,
                    DirType="labels",
                    SampleID=SampleID,
                    Dataset=self.dataset_name,
                    **image_metadata,
                    **kwargs,
                )  
            
            else:    
                self._writer.save(
                    image,
                    DirType="images",
                    SampleID=f"{SampleID}_{nnUNet_MODALITY_MAP[image.metadata['Modality']]}",
                    Dataset=self.dataset_name,
                    **image_metadata,
                    **kwargs,
                )
        
        sample_metadata = {
            "SampleID": SampleID,
            "roi_names": roi_names,
            "num_segmentations": num_segmentations,
            **kwargs
        }

        return sample_metadata
    
    def finalize_dataset(self, query: str) -> None:
        """Finalize dataset by generating preprocessing scripts and dataset JSON configuration."""
        generate_nnunet_scripts(self.root_directory, self.dataset_id)

        # Construct channel names mapping
        channel_names = {
            channel_num.lstrip('0') or '0': modality
            for modality, channel_num in nnUNet_MODALITY_MAP.items()
            if modality in query.split(",")
        }

        # Count the number of training cases
        num_training_cases = sum(
            1 for file in (self.root_directory / "imagesTr").iterdir() 
            if file.is_file()
        )

        generate_dataset_json(
            self.root_directory,
            channel_names=channel_names,
            labels={"background": 0, **self.roi_indices},
            num_training_cases=num_training_cases,
            file_ending=self.file_ending,
        )


if __name__ == "__main__":
    import json

    from rich import print  # noqa

    from imgtools.dicom.crawl import Crawler, CrawlerSettings
    from imgtools.dicom.dicom_metadata import MODALITY_TAGS
    from imgtools.dicom.interlacer import Interlacer
    from imgtools.io.loaders import SampleInput

    dicom_dir = Path("data")

    crawler_settings = CrawlerSettings(
        dicom_dir=dicom_dir,
        n_jobs=12,
        force=False
    )

    crawler = Crawler.from_settings(crawler_settings)

    interlacer = Interlacer(crawler.db_csv)
    interlacer.visualize_forest()

    query = "CT,RTSTRUCT"
    samples = interlacer.query(query)

    roi_names = {"GTV": "GTV.*"}
    input = SampleInput(crawler.db_json, roi_names=roi_names, ignore_missing_regex=True)

    context_keys = list(
        set.union(*[MODALITY_TAGS["ALL"], 
                    *[MODALITY_TAGS.get(modality, {}) for modality in query.split(",")]]
                )
    )

    roi_indices = {
        name: idx+1 for idx, name in enumerate(roi_names.keys())
    }
    output = nnUNetOutput(
        root_directory=Path(".imgtools/data/output_2").resolve(), 
        roi_indices=roi_indices,
        dataset_name=dicom_dir.name, 
        writer_type="nifti", 
        context_keys=context_keys
    )

    output_metadata = []
    for sample_id, sample in enumerate(samples, start=1):
        metadata = output(
            input(sample),
            SampleID=f"{sample_id:03}",
            SplitType="Tr",
        )
        output_metadata.append(metadata)

    print(json.dumps(output_metadata, indent=4))

