from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from imgtools.io.base_classes import BaseOutput
from imgtools.io.writers import ExistingFileMode, NIFTIWriter, AbstractBaseWriter, HDF5Writer
from imgtools.utils import sanitize_file_name
from imgtools.modalities import Scan, Dose, Segmentation, PET 


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
    context_keys: list[str] = field(default_factory=list)
    filename_format: str = field(
        default="{SampleID}/{Modality}_Series-{SeriesInstanceUID}/{ImageID}"
    )
    create_dirs: bool = field(default=True)
    existing_file_mode: ExistingFileMode = field(default=ExistingFileMode.SKIP)
    sanitize_filenames: bool = field(default=True)
    writer_type: str = field(default="nifti")

    @property
    def writer(self) -> AbstractBaseWriter:
        match self.writer_type:
            case "nifti":
                self.filename_format += ".nii.gz"
                return NIFTIWriter
            case "hdf5":
                self.filename_format += ".h5"
                return HDF5Writer
            case _:
                raise ValueError(f"Unsupported writer type: {self.writer_type}")
    
    def __post_init__(self) -> None:
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
        for image in sample:
            # Only include keys that are in the writer context
            image_metadata = {k: image.metadata[k] for k in self._writer.context if k in image.metadata}

            if isinstance(image, Segmentation):
                for name, label in image.roi_indices.items():
                    ImageID = sanitize_file_name(name)
                    out_path = self._writer.resolve_path(
                        ImageID=ImageID, 
                        **image_metadata, 
                        **kwargs
                    )

                    identifier = 0
                    while out_path.exists():
                        identifier += 1
                        out_path = self._writer.resolve_path(
                            ImageID=f"{ImageID}_{identifier}", 
                            **image_metadata, 
                            **kwargs
                        )

                    if identifier > 0:
                        ImageID = f"{ImageID}_{identifier}"

                    roi_seg = image.get_label(label)
                    self._writer.save(
                        roi_seg, 
                        ImageID=ImageID, 
                        **image_metadata, 
                        **kwargs
                    )    
            
            else:    
                self._writer.save(
                    image,
                    ImageID=image.metadata["Modality"],
                    **image_metadata,
                    **kwargs,
                )

if __name__ == "__main__":
    from rich import print  # noqa
    from imgtools.dicom.crawl import CrawlerSettings, Crawler
    from imgtools.dicom.interlacer import Interlacer
    from imgtools.io.loaders import SampleInput
    from imgtools.transforms import Transformer, Resample
    from imgtools.dicom.dicom_metadata import MODALITY_TAGS

    dicom_dir = Path("data")

    crawler_settings = CrawlerSettings(
        dicom_dir=dicom_dir,
        n_jobs=12,
        force=False
    )

    crawler = Crawler.from_settings(crawler_settings)

    interlacer = Interlacer(crawler.db_csv)
    interlacer.visualize_forest()

    query = "MR,RTSTRUCT,RTDOSE"
    samples = interlacer.query(query)

    input = SampleInput(crawler.db_json)
    transform = Transformer(
        [Resample(1)]
    )
    context_keys = list(
        set.union(*[MODALITY_TAGS["ALL"], 
                    *[MODALITY_TAGS.get(modality, {}) for modality in query.split(",")]]
                )
    )
    output = SampleOutput(root_directory=".imgtools/data/output", writer_type="nifti", context_keys=context_keys)

    for sample_idx, sample in enumerate(samples, start=1):
        output(
            input(sample),
            SampleID=f"{dicom_dir.name}_{sample_idx:03d}",
        )


