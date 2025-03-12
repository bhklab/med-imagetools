from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from imgtools.io.base_classes import BaseOutput
from imgtools.io.writers import ExistingFileMode, NIFTIWriter, AbstractBaseWriter
from imgtools.io.writers.sample_output import CONTEXT_KEYS
from imgtools.modalities import Scan, Dose, Segmentation, PET 

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
    context_keys: list[str] | None = field(default=None)
    filename_format: str = field(
        default="{DirType}{SplitType}/{Dataset}_{SampleID}.nii.gz"
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
            case _:
                raise ValueError(f"Unsupported writer type: {self.writer_type}")
    
    def __post_init__(self) -> None:
        """Initialize the NIFTIWriter with the provided parameters and set up the context."""
        self.context_keys = self.context_keys or CONTEXT_KEYS
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

        self.modality_map = {
            "CT": "0000",
            "MR": "0001",
            "PET": "0002",
        }   

        super().__init__(self._writer)

    def __call__(
            self, 
            sample: list[Scan | Dose | Segmentation | PET], 
            **kwargs: Any) -> None:  # noqa: ANN401
        """Write output data.

        Parameters
        ----------
        data : ImageMaskData
            The data to be written.
        **kwargs : Any
            Keyword arguments for the writing process.
        """
        for item in sample:
            if isinstance(item, Segmentation):
                roi_seg = item.generate_sparse_mask()
                self._writer.save(
                    roi_seg,
                    DirType="labels",
                    **item.metadata,
                    **kwargs,
                )  
            
            else:    
                kwargs["SampleID"] += f"_{self.modality_map[item.metadata['Modality']]}"
                self._writer.save(
                    item,
                    DirType="images",
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
    samples = interlacer.query("CT,RTSTRUCT")

    input = SampleInput(crawler.db_json)
    transform = Transformer(
        [Resample(1)]
    )
    output = nnUNetOutput(root_directory=".imgtools/data/output", writer_type="nifti")

    for sample_id, sample in enumerate(samples, start=1):
        output(
            input(sample),
            SampleID=f"{sample_id:03}",
            SplitType="Tr",
            Dataset="all_test_data",
        )

