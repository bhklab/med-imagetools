from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from imgtools.io.base_classes import BaseOutput
from imgtools.io.types import ImageMask
from imgtools.io.writers import ExistingFileMode, NIFTIWriter
from imgtools.utils import sanitize_file_name


@dataclass
class nnUNetOutput(BaseOutput[ImageMask]):
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
    root_directory: Path = field(default=Path("testdata/niftiwriter"))
    filename_format: str = field(
        default="{DirType}{SplitType}/{Dataset}_{SampleID}.nii.gz"
    )
    create_dirs: bool = field(default=True)
    existing_file_mode: ExistingFileMode = field(default=ExistingFileMode.SKIP)
    sanitize_filenames: bool = field(default=True)

    _writer: NIFTIWriter = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the NIFTIWriter with the provided parameters and set up the context."""
        niftiwriter = NIFTIWriter(
            root_directory=self.root_directory,
            filename_format=self.filename_format,
            create_dirs=self.create_dirs,
            existing_file_mode=self.existing_file_mode,
            sanitize_filenames=self.sanitize_filenames,
        )

        self.modality_map = {
        "CT": "0000",
        "MR": "0001",
        "PET": "0002",
        }   

        context = {k: "" for k in niftiwriter.pattern_resolver.keys}
        context.update({k: "" for k in self.context_keys})
        niftiwriter.set_context(**context)
        super().__init__(niftiwriter)

    @property
    def writer(self) -> NIFTIWriter:
        """NIFTIWriter: The NIFTI writer."""
        return self._writer

    def __call__(self, data: ImageMask, **kwargs: Any) -> None:  # noqa: ANN401
        """Write output data.

        Parameters
        ----------
        data : ImageMaskData
            The data to be written.
        **kwargs : Any
            Keyword arguments for the writing process.
        """

        self._write_data(data, **kwargs)

    def _write_data(self, data: ImageMask, *_: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """Write output data.

        Parameters
        ----------
        key : Any
            The identifier for the data to be written.
        *args : Any
            Positional arguments for the writing process.
        **kwargs : Any
            Keyword arguments for the writing process.
        """

        for roi in data.mask.roi_indices:
            roi_seg = data.mask.get_label(name=roi)
            self.writer.save(
                roi_seg,
                DirType="labels",
                **data.mask.metadata,
                **kwargs,
            )
            break

        kwargs["SampleID"] = f"{kwargs["SampleID"]}_{self.modality_map[data.scan.metadata["Modality"]]}"
        self._writer.save(
            data.scan,
            DirType="images",
            **data.scan.metadata,
            **kwargs,
        )


if __name__ == "__main__":
    import json
    import shutil

    from imgtools.dicom.interlacer import Interlacer
    from imgtools.io.loaders import ImageMaskInput
    from imgtools.dicom.crawl import CrawlerSettings

    shutil.rmtree("testdata/niftiwriter", ignore_errors=True)

    root = Path('.')
    with Path(".imgtools/data/crawldb.json").open("r") as f:
        db = json.load(f)
    interlacer = Interlacer(
        crawl_path=".imgtools/data/crawldb.csv",
    )

    from rich import print

    crawler_settings = CrawlerSettings(
        dicom_dir=Path("data/NSCLC-Radiomics"),
        # dicom_dir=pathlib.Path("data"),
        n_jobs=12,
    )
    loader = ImageMaskInput(crawler_settings=crawler_settings)

    for sample_num, image_mask in enumerate(loader, start=1):
        if sample_num == 1:
            keys = list(image_mask.scan.metadata.keys()) + list(
                image_mask.mask.metadata.keys()
            )
            output = nnUNetOutput(context_keys=keys)
            roi_indices ={"background": 0}
            roi_indices.update(image_mask.mask.roi_indices)
        output( 
            data=image_mask,
            SampleID=f"{sample_num:03d}",
            SplitType="Tr",
            Dataset="NSCLC-Radiomics",
        )

    dataset_json = {
        "channel_names": {}, # TODO: add channel names
        "labels": roi_indices,
        "numTraining": len(loader),
        "file_ending": ".nii.gz",
        "liscense": "hands off!",
    }

    with open("testdata/niftiwriter/dataset.json", "w") as f:
        json.dump(dataset_json, f, indent=4)


