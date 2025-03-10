from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from imgtools.io.base_classes import BaseOutput
from imgtools.io.types import ImageMask
from imgtools.io.writers import ExistingFileMode, NIFTIWriter, AbstractBaseWriter, HDF5Writer
from imgtools.utils import sanitize_file_name
from imgtools.modalities import Scan, Dose, Segmentation, PET 

@dataclass
class SampleOutput(BaseOutput):
    """Class for writing ImageMask data to NIFTI files.
    This class handles writing both image scans and their associated masks to NIFTI files.
    The writer initializes with context keys containing all possible metadata keys
    that could be included in the output's index file.
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
    """
    context_keys: list[str]
    root_directory: Path
    filename_format: str = field(
        default="{PatientID}/{Modality}_Series-{SeriesInstanceUID}/{ImageID}.nii.gz"
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
        """Initialize the NIFTIWriter with the provided parameters and set up the context."""
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

    def __call__(self, data: list[Scan | Dose | Segmentation | PET], 
                 **kwargs: Any) -> None:  # noqa: ANN401
        """Write output data.

        Parameters
        ----------
        data : ImageMaskData
            The data to be written.
        **kwargs : Any
            Keyword arguments for the writing process.
        """
        for item in data:
            if isinstance(item, Segmentation):
                for roi in item.roi_indices:
                        roi_seg = item.get_label(name=roi)
                        self._writer.save(
                            roi_seg,
                            ImageID=f"{sanitize_file_name(roi)}",
                            **item.metadata,
                            **kwargs,
                        )      
            
            else:    
                self._writer.save(
                    item,
                    ImageID=item.metadata['Modality'],
                    **item.metadata,
                    **kwargs,
                )

if __name__ == "__main__":
    from rich import print  # noqa
    from imgtools.dicom.interlacer import Interlacer
    from imgtools.io.loaders.sample_loader import SampleLoader
    from imgtools.dicom.crawl import CrawlerSettings, Crawler

    crawler_settings = CrawlerSettings(
        dicom_dir=Path("data"),
        n_jobs=12,
        force=True
    )

    crawler = Crawler.from_settings(crawler_settings)

    interlacer = Interlacer(crawler.db_csv)
    interlacer.visualize_forest()
    samples = interlacer.query("CT,RTSTRUCT")

    loader = SampleLoader(crawler.db_json)

    for sample_id, sample in enumerate(samples, start=1):
        print(sample)
        loaded_samples = loader.load(sample)

        if sample_id == 1:
            keys = set().union(*[set(item.metadata.keys()) for item in loaded_samples])
            print(keys)
            writer = SampleOutput(root_directory=".imgtools/data/output", writer_type="nifti", context_keys=keys)

        case_id = f"Case-{sample_id}"
        writer(loaded_samples)



