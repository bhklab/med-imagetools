from __future__ import annotations

import multiprocessing
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Sequence, cast

from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    field_validator,
    model_validator,
)

from imgtools.coretypes import MedImage
from imgtools.coretypes.masktypes import (
    SEG,
    ROIMatcher,
    ROIMatchFailurePolicy,
    ROIMatchStrategy,
    RTStructureSet,
    Valid_Inputs as ROIMatcherInputs,
    create_roi_matcher,
)
from imgtools.dicom.crawl import Crawler
from imgtools.dicom.interlacer import Interlacer, SeriesNode
from imgtools.io.readers import MedImageT, read_dicom_auto
from imgtools.io.validators import (
    validate_modalities,
)
from imgtools.loggers import logger

if TYPE_CHECKING:
    from imgtools.coretypes.base_masks import VectorMask

__all__ = ["SampleInput"]


class SampleInput(BaseModel):
    """
    Configuration model for processing medical imaging samples.

    This class provides a standardized configuration for loading and processing
    medical imaging data, including DICOM crawling and ROI matching settings.

    Attributes
    ----------
    directory : Path
        Directory containing the input files. Must exist and be readable.
    dataset_name : str | None
        Optional name for the dataset. Defaults to the base name of the input directory.
    update_crawl : bool
        Whether to force a new crawl even if one exists. Default is False.
    n_jobs : int
        Number of jobs to run in parallel. Default is (CPU cores - 2) or 1.
    modalities : list[str] | None
        List of modalities to include. None means include all modalities.
    roi_matcher : ROIMatcher
        Configuration for matching regions of interest in the images.


    Examples
    --------
    >>> from imgtools.io.loaders.sample_input import (
    ...     SampleInput,
    ... )
    >>> config = SampleInput(
    ...     directory="data/NSCLC-Radiomics"
    ... )
    >>> config.dataset_name
    'NSCLC-Radiomics'

    >>> # Using the factory method with ROI matching parameters
    >>> config = SampleInput.build(
    ...     directory="data/NSCLC-Radiomics",
    ...     roi_match_map={
    ...         "GTV": ["GTV.*"],
    ...         "PTV": ["PTV.*"],
    ...     },
    ...     roi_ignore_case=True,
    ...     roi_handling_strategy="merge",
    ... )
    """

    directory: Path = Field(
        description="Path to the input directory containing DICOM files. Absolute path or relative to the current working directory.",
        title="Input Directory",
        examples=["data/NSCLC-Radiomics", "/absolute/path/to/dicom/data"],
    )
    dataset_name: str | None = Field(
        default=None,
        description="Name of the dataset, defaults to input directory base name if not provided. Used for organizing outputs and labeling results.",
        title="Dataset Name",
        min_length=1,
        max_length=100,
        examples=["NSCLC-Radiomics", "Head-Neck-PET-CT"],
    )
    update_crawl: bool = Field(
        default=False,
        description="Force recrawl even if crawl data already exists. Set to True when directory contents have changed or to refresh metadata cache.",
        title="Update DICOM Crawl",
        json_schema_extra={"x-display-name": "Force Directory Recrawl"},
    )
    n_jobs: int = Field(
        default=max(1, multiprocessing.cpu_count() - 2),
        description="Number of parallel jobs to run for DICOM processing. Default reserves 2 cores for system operations.",
        title="Parallel Jobs",
        ge=1,  # Greater than or equal to 1
        le=multiprocessing.cpu_count(),  # Less than or equal to available cores
        examples=[4, 8, 12],
    )
    modalities: list[str] | None = Field(
        default=None,
        description="List of DICOM modalities to include in processing. None means include all modalities. Common values include 'CT', 'MR', 'PT', 'RTSTRUCT', 'RTDOSE', 'SEG'.",
        title="DICOM Modalities",
        examples=[
            ["CT", "RTSTRUCT"],
            ["CT", "PT", "RTSTRUCT", "RTDOSE"],
            ["MR", "SEG"],
        ],
    )
    roi_matcher: ROIMatcher = Field(
        default_factory=lambda: ROIMatcher(match_map={"ROI": [".*"]}),
        description="Configuration for ROI (Region of Interest) matching in segmentation data. Defines how regions are identified, matched and processed from RTSTRUCT or SEG files.",
        title="ROI Matcher Configuration",
    )
    _crawler: Crawler | None = PrivateAttr(default=None)
    _interlacer: Interlacer | None = PrivateAttr(default=None)

    @field_validator("modalities")
    @classmethod
    def _validate_modalities(cls, v: list[str] | None) -> list[str] | None:
        return validate_modalities(v)

    @model_validator(mode="after")
    def _set_default_dataset_name(self) -> "SampleInput":
        if self.dataset_name is None:
            self.dataset_name = self.directory.name
            logger.debug(
                f"Using input directory name as dataset name: {self.dataset_name}"
            )
        return self

    @classmethod
    def build(
        cls,
        directory: str | Path,
        dataset_name: str | None = None,
        update_crawl: bool = False,
        n_jobs: int | None = None,
        modalities: list[str] | None = None,
        roi_match_map: ROIMatcherInputs = None,
        roi_ignore_case: bool = True,
        roi_handling_strategy: str | ROIMatchStrategy = ROIMatchStrategy.MERGE,
        roi_allow_multi_key_matches: bool = True,
        roi_on_missing_regex: str | ROIMatchFailurePolicy = (
            ROIMatchFailurePolicy.IGNORE
        ),
    ) -> "SampleInput":
        """Create a SampleInput with separate parameters for ROIMatcher.

        This factory method allows users to specify ROIMatcher parameters directly
        instead of constructing a objects separately.

        Parameters
        ----------
        cls : class
            The SampleInput class
        directory : str | Path
            Directory containing the input files
        dataset_name : str | None, optional
            Name of the dataset, by default None (uses input directory name)
        update_crawl : bool, optional
            Whether to force recrawling, by default False
        n_jobs : int | None, optional
            Number of parallel jobs, by default None (uses CPU count - 2)
        modalities : list[str] | None, optional
            List of modalities to include, by default None (all)
        roi_match_map : ROIMatcherInputs, optional
            ROI matching patterns, by default None
        roi_ignore_case : bool, optional
            Whether to ignore case in ROI matching, by default True
        roi_handling_strategy : str | ROIMatchStrategy, optional
            Strategy for handling ROI matches, by default ROIMatchStrategy.MERGE
        roi_allow_multi_key_matches : bool, default=True
            Whether to allow one ROI to match multiple keys in the match_map.
        roi_on_missing_regex : str | ROIMatchFailurePolicy, optional
            How to handle when no ROI matches any pattern in match_map.

        Returns
        -------
        SampleInput
            Configured SampleInput instance
        """
        # Convert string strategy to enum if needed
        if isinstance(roi_handling_strategy, str):
            roi_handling_strategy = ROIMatchStrategy(
                roi_handling_strategy.lower()
            )

        if isinstance(roi_on_missing_regex, str):
            roi_on_missing_regex = ROIMatchFailurePolicy(
                roi_on_missing_regex.lower()
            )

        # Create the ROIMatcher
        roi_matcher = create_roi_matcher(
            roi_match_map,
            handling_strategy=roi_handling_strategy,
            ignore_case=roi_ignore_case,
            allow_multi_key_matches=roi_allow_multi_key_matches,
            on_missing_regex=roi_on_missing_regex,
        )
        num_jobs = n_jobs or max(1, multiprocessing.cpu_count() - 2)

        # Create the SampleInput
        return cls(
            directory=Path(directory),
            dataset_name=dataset_name,
            update_crawl=update_crawl,
            n_jobs=num_jobs,
            modalities=modalities,
            roi_matcher=roi_matcher,
        )

    @classmethod
    def default(cls) -> "SampleInput":
        """Create a default SampleInput instance."""
        return cls.build(directory="./data")

    ###################################################################
    # Interlacer methods
    ###################################################################

    @property
    def crawler(self) -> Crawler:
        """Get the Crawler instance, initializing it if needed.

        Returns
        -------
        Crawler
            A DICOM crawler instance, initialized with the current configuration.

        Notes
        -----
        The crawler is lazily initialized on first access.
        """
        if self._crawler is None:
            crawler = Crawler(
                dicom_dir=self.directory,
                dataset_name=self.dataset_name,
                force=self.update_crawl,
                n_jobs=self.n_jobs,
            )
            crawler.crawl()
            self._crawler = crawler
        return self._crawler

    @property
    def interlacer(self) -> Interlacer:
        """Get the Interlacer instance, initializing it if needed.

        Returns
        -------
        Interlacer
            An Interlacer instance tied to the current crawler.

        Notes
        -----
        The interlacer is lazily initialized on first access, which may trigger
        crawler initialization if it hasn't been accessed yet.
        """
        if self._interlacer is None:
            self._interlacer = Interlacer(crawl_index=self.crawler.index)
        return self._interlacer

    def print_tree(self) -> None:
        self.interlacer.print_tree(input_directory=self.directory)

    def query(self, modalities: str | None = None) -> list[list[SeriesNode]]:
        """Query the interlacer for a specific modality."""
        if modalities is None:
            modalities = ",".join(self.modalities) if self.modalities else "*"
        return self.interlacer.query(modalities)

    ###################################################################
    # Loading methods
    ###################################################################

    def _read_series(
        self,
        series_uid: str,
        modality: str,
        folder: str,
        load_subseries: bool = False,
    ) -> list[MedImageT]:
        """
        Read a medical image series from DICOM files.

        This function loads one or more medical images from DICOM files based on their series UID.

        First, we locate the directory containing the DICOM files, then we extract file paths
        for all instances in the series. If load_subseries is True, we'll load each subseries
        as a separate image; otherwise, we'll combine all instances into a single image.

        Parameters
        ----------
        series_uid : str
            Unique identifier for the DICOM series to load
        modality : str
            The imaging modality (CT, MR, PT, etc.) of the series
        folder : str
            The folder path containing the DICOM files
        load_subseries : bool, default=False
            Whether to load subseries as separate images

        Returns
        -------
        list[MedImageT]
            A list of loaded medical images, one per subseries if load_subseries=True,
            otherwise a list containing a single combined image

        Raises
        ------
        FileNotFoundError
            If the specified folder does not exist
        """
        # we assume that all subseries are in the same directory
        root_dir = self.directory.parent / folder

        if not root_dir.exists():
            msg = f"Directory does not exist: {root_dir}"
            raise FileNotFoundError(msg)

        file_name_sets = []
        series_info = self.crawler.crawl_db_raw[series_uid]
        if load_subseries:
            for subseries in series_info:
                file_name_sets.append(
                    [
                        (root_dir / file_name).as_posix()
                        for file_name in series_info[subseries][
                            "instances"
                        ].values()
                    ]
                )
        else:
            if len(series_info) > 1:
                msg = (
                    f"Series {series_uid} contains multiple subseries, but "
                    "load_subseries is set to False. Combining into one image."
                )
                logger.warning(msg, folder=folder, modality=modality)
            file_name_sets.append(
                [
                    (root_dir / file_name).as_posix()
                    for subseries in series_info
                    for file_name in series_info[subseries][
                        "instances"
                    ].values()
                ]
            )

        # load the series
        return [
            read_dicom_auto(
                path=root_dir.as_posix(),
                modality=modality,
                file_names=file_name_set,
                series_id=series_uid,
            )
            for file_name_set in file_name_sets
        ]

    def __call__(  # noqa: PLR0912
        self,
        sample: Sequence[SeriesNode],
        load_subseries: bool = False,
    ) -> Sequence[MedImage | VectorMask]:
        """
        Load a complete sample of medical images and masks from DICOM series.

        This function processes a collection of DICOM series and loads them as
        `MedImage` or `VectorMask` objects.

        It automatically identifies a reference image (preferring
        CT, then MR, then PT) and loads all other modalities relative to this reference.

        First, we group the input series by modality, then we identify and load a reference
        image.

        All other series (RTSTRUCT, SEG, additional CT/MR/PT) are loaded with
        reference to the primary image to ensure proper alignment.

        Parameters
        ----------
        sample : Sequence[SeriesNode]
            Collection of series nodes representing the DICOM series to load
        load_subseries : bool, default=False
            Whether to load subseries as separate images

        Returns
        -------
        Sequence[MedImage | VectorMask]
            Collection of loaded medical images and vector masks, with the reference
            image always as the first element

        Raises
        ------
        ValueError
            If no suitable reference image (CT, MR, or PT) is found

        Notes
        -----
        RTSTRUCT and SEG modalities are loaded as VectorMask using the reference image
        for spatial alignment. Other modalities (CT, MR, PT, RTDOSE) are loaded as
        MedImage objects.
        """
        # group list by modality
        by_mod: defaultdict[str, list[SeriesNode]] = defaultdict(list)
        for series in sample:
            by_mod[series.Modality].append(series)

        reference_modality = (
            "CT"
            if "CT" in by_mod
            else "MR"
            if "MR" in by_mod
            else "PT"
            if "PT" in by_mod
            else None
        )
        if not reference_modality:
            raise ValueError(
                "No CT, MR, or PT series found to use as reference."
            )
        if len(by_mod[reference_modality]) > 1:
            msg = (
                f"Found {len(by_mod[reference_modality])} "
                f"{reference_modality} series, "
                "using the first one as reference."
            )
            logger.warning(msg, reference_list=by_mod[reference_modality])

        # Load the first found reference series
        reference_series = by_mod[reference_modality].pop(0)
        reference_images = self._read_series(
            series_uid=reference_series.SeriesInstanceUID,
            modality=reference_modality,
            folder=reference_series.folder,
            load_subseries=load_subseries,
        )

        images: Sequence[MedImage] = []

        # hack to satisfy mypy for now
        reference_scans = cast("list[MedImage]", reference_images)

        # Extract the first (of possibly many subseries) as the reference image
        reference_image = reference_scans[0]
        images = reference_scans[1:]
        # Load the rest of the series
        for modality, series_nodes in by_mod.items():
            if modality == reference_modality:
                # TODO:: maybe implement some check here in case we loading
                # another of same reference modality?
                continue

            # for all other series, we load them and insert them into the
            # images list
            for series in series_nodes:
                image = self._load_non_ref_image(
                    load_subseries, reference_image, modality, series
                )
                if image is not None:
                    images.append(image)

        return [reference_image] + images

    def _load_non_ref_image(
        self,
        load_subseries: bool,
        reference_image: MedImage,
        modality: str,
        series: SeriesNode,
    ) -> MedImage | VectorMask | None:
        """Load a non-reference image series based on modality."""
        series_info = self.crawler.get_series_info(
            series_uid=series.SeriesInstanceUID
        )
        try:
            match modality:
                case "RTSTRUCT" | "SEG":
                    mask_klass = (
                        RTStructureSet if modality == "RTSTRUCT" else SEG
                    )
                    vm = mask_klass.from_dicom(
                        dicom=self.directory.parent / series.folder,
                        metadata=series_info,  # pass along metadata
                    ).get_vector_mask(
                        reference_image=reference_image,
                        roi_matcher=self.roi_matcher,
                    )
                    return vm
                case "PT" | "CT" | "MR" | "RTDOSE":
                    misc = self._read_series(
                        series_uid=series.SeriesInstanceUID,
                        modality=modality,
                        folder=series.folder,
                        load_subseries=load_subseries,
                    )
                    # if len (misc) > 1, that means that somehow a non-reference
                    # image has multiple subseries, which is not expected
                    # and we should handle this at some point
                    assert isinstance(misc[0], MedImage) and len(misc) == 1
                    return misc[0]
                case _:
                    msg = f"Unsupported modality: {modality}"
                    raise ValueError(msg)
        except Exception as e:
            logger.error(
                f"Error loading series {series.SeriesInstanceUID}: {e}"
            )
            return None


if __name__ == "__main__":  # pragma: no cover
    from rich import print  # noqa: A004, F401
    from tqdm import tqdm  # noqa: A003

    from imgtools.io.sample_output import ExistingFileMode, SampleOutput
    from imgtools.loggers import tqdm_logging_redirect

    medinput = SampleInput(
        directory=Path("data/RADCURE"),
        update_crawl=True,
        n_jobs=12,
        dataset_name="RADCURE",
        modalities=["CT", "RTSTRUCT"],
        roi_matcher=ROIMatcher(
            match_map={
                "GTV": ["GTVp"],
                "NODES": ["GTVn_.*"],
                "LPLEXUS": ["BrachialPlex_L"],
                "RPLEXUS": ["BrachialPlex_R"],
                "BRAINSTEM": ["Brainstem"],
                "LACOUSTIC": ["Cochlea_L"],
                "RACOUSTIC": ["Cochlea_R"],
                "ESOPHAGUS": ["Esophagus"],
                "LEYE": ["Eye_L"],
                "REYE": ["Eye_R"],
                "LARYNX": ["Larynx"],
                "LLENS": ["Lens_L"],
                "RLENS": ["Lens_R"],
                "LIPS": ["Lips"],
                "MANDIBLE": ["Mandible_Bone"],
                "LOPTIC": ["Nrv_Optic_L"],
                "ROPTIC": ["Nrv_Optic_R"],
                "CHIASM": ["OpticChiasm"],
                "LPAROTID": ["Parotid_L"],
                "RPAROTID": ["Parotid_R"],
                "CORD": ["SpinalCord"],
            },
            allow_multi_key_matches=False,  # if True, an ROI can match multiple keys
            handling_strategy=ROIMatchStrategy.SEPARATE,
            ignore_case=True,
            on_missing_regex=ROIMatchFailurePolicy.WARN,
        ),
    )
    medoutput = SampleOutput(
        directory=Path("temp_outputs/RADCURE_PROCESSED"),
        existing_file_mode=ExistingFileMode.OVERWRITE,
        extra_context={"SampleNumber": "test"},
    )
    query_string = "CT,RTSTRUCT"

    sample_sets = medinput.interlacer.query(
        query_string=query_string,
        group_by_root=True,
    )
    with tqdm_logging_redirect():
        for series in tqdm(
            sample_sets,
            desc="Loading series",
            unit="series",
            leave=False,
            total=len(sample_sets),
        ):
            try:
                result = medinput(
                    sample=series,
                    load_subseries=False,
                )
            except ValueError as e:
                logger.error(f"Error loading series: {e}")
                continue
            medoutput(result)
