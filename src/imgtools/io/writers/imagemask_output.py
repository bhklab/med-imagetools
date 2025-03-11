from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from imgtools.io.base_classes import BaseOutput
from imgtools.io.types import ImageMask
from imgtools.io.writers import ExistingFileMode, NIFTIWriter
from imgtools.utils import sanitize_file_name


@dataclass
class ImageMaskOutput(BaseOutput[ImageMask]):
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
        default="{PatientID}/{Modality}_Series-{SeriesInstanceUID}/{ImageID}.nii.gz"
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

        self._writer.save(
            data.scan,
            ImageID="reference",
            **data.scan.metadata,
            **kwargs,
        )

        mask = data.mask

        for roi in mask.roi_indices:
            roi_seg = mask.get_label(name=roi)
            self._writer.save(
                roi_seg,
                ImageID=f"{sanitize_file_name(roi)}",
                **mask.metadata,
                **kwargs,
            )


# if __name__ == "__main__":
#     import json
#     import shutil

#     from tqdm import tqdm

#     from imgtools.io.loaders.utils import (
#         read_dicom_auto,
#         read_dicom_rtstruct,
#     )
#     from imgtools.loggers import tqdm_logging_redirect
#     from imgtools.modalities.interlacer import Interlacer

#     shutil.rmtree("testdata/niftiwriter", ignore_errors=True)

#     root = Path("testdata")
#     with Path(root, ".imgtools/Head-Neck-PET-CT/crawldb.json").open("r") as f:
#         db = json.load(f)
#     interlacer = Interlacer(
#         crawl_path="testdata/.imgtools/Head-Neck-PET-CT/crawldb.csv",
#         query_branches=True,
#     )

#     samples = interlacer.query("CT,RTSTRUCT")
#     print(f"Found {len(samples)} pairs of CT and RTSTRUCT series")  # noqa: T201
#     # Extract unique pairs from the samples list
#     unique_pairs = {
#         tuple((entry[0]["Series"], entry[1]["Series"])) for entry in samples
#     }

#     # Convert back to a list of dictionaries
#     samples = [
#         [
#             {"Series": pair[0], "Modality": "CT"},
#             {"Series": pair[1], "Modality": "RTSTRUCT"},
#         ]
#         for pair in unique_pairs
#     ]
#     print(f"Found {len(samples)} UNIQUE pairs of CT and RTSTRUCT series")  # noqa: T201
#     output: ImageMaskOutput
#     samplesets = list(enumerate(samples[:10], start=1))
#     with tqdm_logging_redirect():
#         for sample_num, (image_series, mask_series) in tqdm(
#             samplesets, total=len(samplesets)
#         ):
#             imagemeta = db[image_series["Series"]]
#             maskmeta = db[mask_series["Series"]]

#             # get folder quick
#             image_folder = root.absolute() / (
#                 str(dpath.get(imagemeta, "**/folder"))
#             )
#             image_filenames = [
#                 str((image_folder / f).as_posix())
#                 for f in list(dpath.get(imagemeta, "**/instances").values())  # type: ignore
#             ]

#             mask_folder = Path(str(dpath.get(maskmeta, "**/folder")))
#             mask_filenames = [
#                 root / mask_folder / f
#                 for f in list(dpath.get(maskmeta, "**/instances").values())  # type: ignore
#             ]
#             try:
#                 assert len(mask_filenames) == 1, (
#                     f"Expected 1 mask file, got {mask_filenames}"
#                 )
#             except AssertionError as e:
#                 logger.error(
#                     f"{e}",
#                     image_series=image_series,
#                     mask_series=mask_series,
#                     imagemeta=imagemeta,
#                     maskmeta=maskmeta,
#                 )
#                 raise e

#             image_scan = read_dicom_auto(
#                 path=str(image_folder),
#                 series=image_series["Series"],
#                 file_names=image_filenames,
#             )
#             assert isinstance(image_scan, Scan)

#             rt = read_dicom_rtstruct(
#                 mask_filenames[0], roi_name_pattern="GTV.*"
#             )
#             seg = rt.to_segmentation(
#                 image_scan, roi_names="GTV.*", continuous=False
#             )
#             if not seg:
#                 continue

#             if sample_num == 1:
#                 keys = list(image_scan.metadata.keys()) + list(
#                     seg.metadata.keys()
#                 )
#                 output = ImageMaskOutput(context_keys=keys)

#             output(
#                 ImageMaskData(image=image_scan, mask=seg),
#                 SampleID=f"{sample_num:03d}",
#             )
