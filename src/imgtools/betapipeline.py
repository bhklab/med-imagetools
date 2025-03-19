import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from joblib import Parallel, delayed  # type: ignore
from tqdm import tqdm

from imgtools.dicom import Crawler, Interlacer
from imgtools.dicom.dicom_metadata import MODALITY_TAGS
from imgtools.io import SampleInput, SampleOutput, nnUNetOutput
from imgtools.loggers import logger, tqdm_logging_redirect
from imgtools.transforms import Resample, Transformer, WindowIntensity
from imgtools.utils.nnunet import create_train_test_mapping

@dataclass
class BetaPipeline():
    """
    This pipeline automatically goes through the following steps:
        1. Crawl and connect modalities as samples
        2. Load individual samples
        3. Apply transforms to each image
        4. Save each sample as desired directory structure

    Parameters
    ----------
    input_directory : Path
        Input directory containing the raw DICOM data
    output_directory : Path
        Output directory where the processed data will be saved
    dcm_extension : str
        Extension of the DICOM files, default is "dcm"
    update_crawl : bool
        Whether to update the crawl data if it already exists, default is False
    query : str
        Comma-separated string of modalities to query, default is "CT,RTSTRUCT"
    spacing : tuple[float]
        Spacing of the resampled image, default is (1.0, 1.0, 0.0)
    window : float | None
        Window level of the intensity adjustment, default is None
    level : float | None
        Window width of the intensity adjustment, default is None
    nnunet : bool
        Whether to format the output for nnU-Net, default is False
    train_size : float
        Proportion of samples to use for training/test for nnU-Net, default is 1.0
        Only used if nnunet is True
    random_state : int
        Random seed for shuffling the samples for nnU-Net, default is 42
    require_all_rois : bool
        Whether all ROIs must be present in each sample for nnU-Net, default is True
    n_jobs : int
        Number of jobs to run in parallel, default is -1
    dataset_name : str | None
        Name of the dataset, default is None
    writer_type : str
        Type of writer to use, default is "nifti"
    roi_yaml_path : Path | None
        Path to the YAML file containing the ROI names, default is None
    ignore_missing_regex : bool
        Whether to ignore missing ROIs from roi_yaml_path, default is False
        This is set to True for nnU-Net
    roi_select_first : bool
        Whether to select only the first ROI match from roi_yaml_path, default is False
    roi_separate : bool
        Whether to separate matches from roi_yaml_path, default is False
    """

    input_directory: Path
    output_directory: Path

    # Crawl parameters
    dcm_extension: str = "dcm"
    update_crawl: bool = False

    # Interlacer parameters
    query: str = "CT,RTSTRUCT"

    # Transformer parameters
    spacing: tuple[float] = (1.0, 1.0, 0.0)
    window: float | None = None
    level: float | None = None

    # nnU-Net parameters
    nnunet: bool = False
    train_size: float = 1.0
    random_state: int = 42
    require_all_rois: bool = True

    n_jobs: int = -1
    dataset_name: str | None = None
    writer_type: str = "nifti"

    # ROI parameters
    roi_yaml_path: Path | None = None
    ignore_missing_regex: bool = False
    roi_select_first: bool = False
    roi_separate: bool = False

    def __post_init__(self) -> None:
        self.dataset_name = self.dataset_name or self.input_directory.name

        ### CRAWL/CONNECT
        self.crawl = Crawler(
            dicom_dir=self.input_directory,
            n_jobs=self.n_jobs,
            dcm_extension="dcm",
            force=self.update_crawl,
            dataset_name=self.dataset_name,
        )
        self.lacer = Interlacer(self.crawl.db_csv) # uses CSV of crawl

        ### INPUT
        self.roi_names = None
        if self.roi_yaml_path:
            with self.roi_yaml_path.open() as f:
                self.roi_names = yaml.safe_load(f)

        if self.nnunet:
            if self.roi_names is None:
                raise ValueError("ROI names must be provided for nnU-Net")
            self.roi_indices = {name: idx+1 for idx, name in enumerate(self.roi_names)}

            if not self.ignore_missing_regex:
                logger.warning(
                    "Set ignore_missing_regex=True to ignore missing ROIs for nnU-Net"
                )
                self.ignore_missing_regex = True 

        self.input = SampleInput(
            crawl_path=self.crawl.db_json, # uses JSON of crawl
            roi_names=self.roi_names,
            ignore_missing_regex=self.ignore_missing_regex,
            roi_select_first=self.roi_select_first,
            roi_separate=self.roi_separate,
        )   

        ### TRANSFORM
        transforms = [Resample(self.spacing)]
        # add W/L adjustment to transforms
        if self.window is not None and self.level is not None:
            transforms.append(WindowIntensity(self.window, self.level))

        self.transformer = Transformer(transforms)

        ### OUTPUT
        context_keys = list(
        set.union(*[MODALITY_TAGS["ALL"], 
                    *[MODALITY_TAGS.get(modality, {}) for modality in self.query.split(",")]]
                )
        )

        if self.nnunet:
            self.output = nnUNetOutput(
                root_directory=self.output_directory,
                roi_indices=self.roi_indices,
                dataset_name=self.dataset_name,
                context_keys=context_keys, 
                writer_type=self.writer_type,
                require_all_rois=self.require_all_rois
            )
        else:
            self.output = SampleOutput(
                context_keys=context_keys, 
                root_directory=self.output_directory, 
                writer_type=self.writer_type
            )

    def process_one_sample(self, sample: list[dict[str, str]], idx: int) -> dict[str, Any]:
        # Load images
        images = self.input(sample)
            
        # Apply transforms to all images
        images = self.transformer(images)

        # Save transformed images
        if self.nnunet:
            metadata = self.output(
                images,
                SampleID=f"{idx:03}",
                SplitType=self.train_test_mapping[idx],
            )
        else: 
            metadata = self.output(
                images, 
                SampleID=f"{self.input_directory.name}_{idx:03d}"
            ) 
        
        metadata["SampleID"] = f"{idx:03d}"

        # Return metadata from each sample
        return metadata

    def run(self) -> None:
        # Query Interlacer for samples of desired modalities
        self.samples = self.lacer.query(self.query)

        # Before processing
        if self.nnunet:
            self.train_test_mapping = create_train_test_mapping(
                list(range(1, len(self.samples)+1)), 
                self.train_size, self.random_state
            )

        with tqdm_logging_redirect():
            # Process the samples in parallel
            self.metadata = Parallel(n_jobs=self.n_jobs)(
                delayed(self.process_one_sample)(sample, idx) 
                for idx, sample in enumerate(tqdm(
                    self.samples,
                    desc="Processing Samples",
                    mininterval=1,
                    leave=False,
                ), start=1)
            )

        metadata_path = self.input_directory.parent / ".imgtools" / self.dataset_name / "metadata.json"
        with metadata_path.open("w") as f:
            json.dump(self.metadata, f, indent=4)

        # After processing
        if self.nnunet:
            self.output.finalize_dataset(self.query)

    
def main() -> None:
    autopipe = BetaPipeline(
        input_directory=Path("data"),
        output_directory=Path("output"),
        query="CT,RTSTRUCT",
        n_jobs=1,
        nnunet=True,
        roi_yaml_path=Path("roi.yaml"),
        # update_crawl=True,
    )
    autopipe.run()


if __name__ == "__main__":
    main()
