from dataclasses import dataclass
from pathlib import Path
from typing import Any

import dpath

from imgtools.io.base_classes import BaseOutput
from imgtools.io.writers import ExistingFileMode, NIFTIWriter
from imgtools.logging import logger
from imgtools.modalities import Scan, Segmentation
from imgtools.utils import sanitize_file_name


@dataclass
class ImageMaskData:
    image: Scan
    mask: Segmentation


class ImageMaskOutput(BaseOutput[ImageMaskData]):
    def __init__(self, context_keys: list[str]) -> None:
        """Initialize the ImageMaskOutput class.

        When dumping to the index file, the writer asssumes
        that the keys used for each `save` call are the only headers that
        matter.
        However, since image and mask have different metadata, we need to
        pre-set the header with all the possible keys that could be used.

        Parameters
        ----------
        context_keys : list[str]
            All possible keys that could be passed into the `save` method
            and that should be dumped into the index file.
        """
        niftiwriter = NIFTIWriter(
            root_directory=Path("testdata/niftiwriter"),
            filename_format="{SampleID}_{PatientID}/{Modality}_Series-{SeriesInstanceUID}/{ImageID}.nii.gz",
            create_dirs=True,
            existing_file_mode=ExistingFileMode.SKIP,
            sanitize_filenames=True,
        )

        context = {k: "" for k in niftiwriter.pattern_resolver.keys}
        context.update({k: "" for k in context_keys})
        niftiwriter.set_context(**context)
        super().__init__(niftiwriter)

    def __call__(self, data: ImageMaskData, *_: Any, **kwargs: Any) -> None:  # noqa: ANN401
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
            data.image,
            ImageID="Scan",
            **data.image.metadata,
            **kwargs,
            # **getattr(data.image, "metadata", {}),
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


if __name__ == "__main__":
    import json
    import shutil

    from tqdm import tqdm

    from imgtools.dicom.dicom_metadata import extract_dicom_tags
    from imgtools.io.loaders.utils import (
        read_dicom_auto,
        read_dicom_rtstruct,
    )
    from imgtools.logging import tqdm_logging_redirect
    from imgtools.modalities.interlacer import Interlacer

    shutil.rmtree("testdata/niftiwriter", ignore_errors=True)

    root = Path("testdata")
    with Path(root, ".imgtools/Head-Neck-PET-CT/crawldb.json").open("r") as f:
        db = json.load(f)
    interlacer = Interlacer(
        crawl_path="testdata/.imgtools/Head-Neck-PET-CT/crawldb.csv",
        query_branches=True,
    )

    samples = interlacer.query("CT,RTSTRUCT")
    print(f"Found {len(samples)} pairs of CT and RTSTRUCT series")
    # Extract unique pairs from the samples list
    unique_pairs = {
        tuple((entry[0]["Series"], entry[1]["Series"]))
        for entry in samples
    }

    # Convert back to a list of dictionaries
    samples = [
        [
            {"Series": pair[0], "Modality": "CT"},
            {"Series": pair[1], "Modality": "RTSTRUCT"},
        ]
        for pair in unique_pairs
    ]
    print(f"Found {len(samples)} UNIQUE pairs of CT and RTSTRUCT series")
    output: ImageMaskOutput
    samplesets = list(enumerate(samples[:10], start=1))
    with tqdm_logging_redirect():
        for sample_num, (image_series, mask_series) in tqdm(
            samplesets, total=len(samplesets)
        ):
            imagemeta = db[image_series["Series"]]
            maskmeta = db[mask_series["Series"]]

            # get folder quick
            image_folder = root.absolute() / (
                str(dpath.get(imagemeta, "**/folder"))
            )
            image_filenames = [
                str((image_folder / f).as_posix())
                for f in list(dpath.get(imagemeta, "**/instances").values())  # type: ignore
            ]

            mask_folder = Path(str(dpath.get(maskmeta, "**/folder")))
            mask_filenames = [
                root / mask_folder / f
                for f in list(dpath.get(maskmeta, "**/instances").values())  # type: ignore
            ]
            try:
                assert len(mask_filenames) == 1, (
                    f"Expected 1 mask file, got {mask_filenames}"
                )
            except AssertionError as e:
                logger.error(f"{e}", image_series=image_series, mask_series=mask_series, imagemeta=imagemeta, maskmeta=maskmeta)
                raise e

            image_scan = read_dicom_auto(
                path=str(image_folder),
                series=image_series["Series"],
                file_names=image_filenames,
            )
            assert isinstance(image_scan, Scan)

            rt = read_dicom_rtstruct(mask_filenames[0])
            seg = rt.to_segmentation(
                image_scan, roi_names="GTV.*", continuous=False
            )

            if sample_num == 1:
                keys = list(image_scan.metadata.keys()) + list(
                    seg.metadata.keys()
                )
                output = ImageMaskOutput(context_keys=keys)

            output(
                ImageMaskData(image=image_scan, mask=seg),
                SampleID=f"{sample_num:03d}",
            )
