"""Crawl a directory of (post-DICOM) image files and build an index of scan/mask pairs."""

from pathlib import Path

from pydantic import BaseModel, Field, PrivateAttr

from imgtools.dicom.crawl.crawler import validate_output_dir
from imgtools.loggers import logger, tqdm_logging_redirect
from imgtools.nifti.crawl.parse_niftis import (
    MetadataInput,
    ParseNiftiDirResult,
    parse_nifti_dir,
)


class Crawler(BaseModel):
    """Crawl a directory of image files and extract metadata into an index."""

    # ---- Paths and patterns ----
    nifti_dir: Path = Field(
        description="Path to the root directory containing image files.",
    )
    scan_name_pattern: str = Field(
        description=(
            "Template for scan filenames. Use {placeholders} for path segments. "
            "Example: images/{PatientID}_{Modality}.nii.gz"
        ),
        examples=["images/{PatientID}_{Modality}.nii.gz"],
    )
    mask_name_pattern: str | None = Field(
        description=(
            "Optional template for mask filenames. "
            "Example: masks/{PatientID}_{Modality}_{ROI}.nii.gz"
        ),
        examples=["masks/{PatientID}_{Modality}_{ROI}.nii.gz"],
        default=None,
    )

    # ---- Discovery ----
    extensions: str | list[str] = Field(
        description=(
            "File extension(s) to search for. Single string or list. "
            "Defaults to NIfTI: '.nii.gz', '.nii'."
        ),
        default=[".nii.gz", ".nii"],
    )
    deep: bool = Field(
        description="If True, read each image and run introspection (fingerprint). If False, only path and match metadata.",
        default=False,
    )
    n_jobs: int = Field(
        description="Number of parallel jobs for file introspection. 1 = sequential, -1 = all cores.",
        default=1,
    )

    # ---- Output ----
    output_dir: Path | None = Field(
        description="Where to write the index and cache. Defaults to nifti_dir.parent / '.imgtools'.",
        default=None,
    )
    dataset_name: str | None = Field(
        description="Name for this dataset (used as subdir under output_dir). Defaults to nifti_dir.name.",
        default=None,
    )
    force: bool = Field(
        description="If True, ignore cached results and re-crawl.",
        default=False,
    )

    # ---- Metadata merge ----
    metadata_path: MetadataInput | None = Field(
        description="Path(s) to CSV or JSON to merge into the index. Single path or list.",
        default=None,
    )
    metadata_join_col: str | None = Field(
        description=(
            "Column that must appear as a {placeholder} in the patterns "
            "and in each metadata file. Required when metadata_path is set."
        ),
        default=None,
    )

    _crawl_results: ParseNiftiDirResult | None = PrivateAttr(default=None)

    def crawl(self) -> None:
        """Crawl the directory and build the index."""
        self.output_dir = self.output_dir or self.nifti_dir.parent / ".imgtools"
        validate_output_dir(self.output_dir)

        logger.info(
            "Starting NIFTI crawl.",
            nifti_dir=self.nifti_dir,
            output_dir=self.output_dir,
            dataset_name=self.dataset_name,
        )

        with tqdm_logging_redirect():
            self._crawl_results = parse_nifti_dir(
                nifti_dir=self.nifti_dir,
                scan_name_pattern=self.scan_name_pattern,
                mask_name_pattern=self.mask_name_pattern,
                extensions=self.extensions,
                deep=self.deep,
                n_jobs=self.n_jobs,
                output_dir=self.output_dir,
                dataset_name=self.dataset_name,
                force=self.force,
                metadata_path=self.metadata_path,
                metadata_join_col=self.metadata_join_col,
            )


if __name__ == "__main__":
    # crawler = Crawler(
    #     nifti_dir=Path("TotalsegmentatorMRI_dataset_v100"),
    #     scan_name_pattern="{image_id}/{Modality}.nii.gz",
    #     mask_name_pattern="{image_id}/segmentations/{ROI}.nii.gz",
    #     force=True,
    #     metadata_path=Path("TotalsegmentatorMRI_dataset_v100/meta.csv"),
    #     metadata_join_col="image_id",   
    #     deep=True,
    #     n_jobs=-1,
    # )
    # crawler.crawl()

    crawler = Crawler(
        nifti_dir=Path("final-formatted"),
        scan_name_pattern="images/{disease_site}/{split}/images/{patient_id:d}_{SeriesInstanceUID}.nii.gz",
        mask_name_pattern="images/{disease_site}/{split}/masks/{patient_id:d}_{SeriesInstanceUID}.nii.gz",
        force=True,
        metadata_path=[Path("final-formatted/metadata/patients.csv")],
        metadata_join_col="patient_id",
        deep=True,
        n_jobs=-1,
    )
    crawler.crawl()
