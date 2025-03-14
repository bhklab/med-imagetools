###############################################################
# Example usage:
# python radcure_simple.py ./data/RADCURE/data ./RADCURE_output
###############################################################
from dataclasses import dataclass, field
from pathlib import Path

from joblib import Parallel, delayed  # type: ignore
import yaml

from imgtools.loggers import logger
from imgtools.dicom import Crawler, Interlacer
from imgtools.transforms import Resample, Transformer, WindowIntensity
from imgtools.io import SampleInput, SampleOutput, nnUNetOutput
from imgtools.dicom.dicom_metadata import MODALITY_TAGS
from imgtools.utils.nnunet import (
    create_train_test_mapping, 
    generate_dataset_json, 
    nnUNet_MODALITY_MAP,
    create_preprocess_and_train_scripts
)
from imgtools.modalities import Segmentation

@dataclass
class BetaPipeline():
    """
    This pipeline automatically goes through the following steps:
        1. Crawl and connect modalities as samples
        2. Load individual samples
        3. Apply transforms to each image
        4. Save each sample as desired directory structure
    """

    input_directory: Path
    output_directory: Path

    # Crawl parameters
    dcm_extension: str = "dcm"
    update_crawl: bool = False

    # Interlacer parameters
    query: str = "CT,RTSTRUCT"

    # Transformer parameters
    spacing: tuple[float] = (1.0, 1.0, 0.) #field(default_factory=lambda: Spacing3D(1.0, 1.0, 0.0)) 
    window: float | None = None
    level: float | None = None

    # nnU-Net parameters
    nnunet: bool = False
    train_size: float = 1.0
    random_state: int = 42

    n_jobs: int = -1
    dataset_name: str | None = None
    writer_type: str = "nifti"

    # ROI parameters
    roi_yaml_path: Path | None = None
    ignore_missing_regex: bool = True # Needs to be true for nnU-Net
    roi_select_first: bool = False
    roi_separate: bool = False

    def __post_init__(self) -> None:
        self.dataset_name = self.dataset_name or self.input_directory.name

        self.crawl = Crawler(
            dicom_dir=self.input_directory,
            n_jobs=self.n_jobs,
            dcm_extension="dcm",
            force=self.update_crawl,
            dataset_name=self.dataset_name, # if you want to rename the .imgtools/{dataset_name} folder
        )
        self.lacer = Interlacer(self.crawl.db_csv) # uses CSV of crawl

        ### INPUT
        self.roi_names = None
        if self.roi_yaml_path:
            with self.roi_yaml_path.open() as f:
                self.roi_names = yaml.safe_load(f)

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

        match self.writer_type:
            case "nifti":
                self.file_ending = ".nii.gz"
            case "hdf5":
                self.file_ending = ".h5"
            case _:
                raise ValueError(f"Unknown writer type: {self.writer_type}")

        if self.nnunet:
            if self.roi_names is None:
                raise ValueError("ROI names must be provided for nnU-Net")

            (self.output_directory / "nnUNet_results").mkdir(parents=True, exist_ok=True)
            (self.output_directory / "nnUNet_preprocessed").mkdir(parents=True, exist_ok=True)
            (self.output_directory / "nnUNet_raw").mkdir(parents=True, exist_ok=True)

            used_ids = {
                int(Path(folder).name[7:10]) 
                for folder in (self.output_directory / "nnUNet_raw").glob("*")
                if Path(folder).name.startswith("Dataset")
            }
            print(f"Used IDs: {used_ids}")
            all_ids = set(range(1, 1000))
            self.dataset_id = sorted(all_ids - used_ids)[0]

            self.output_directory = self.output_directory / "nnUNet_raw" / f"Dataset{self.dataset_id:03d}_{self.dataset_name}"

            output_class = nnUNetOutput
        else:
            output_class = SampleOutput
            
        self.output = output_class(
            context_keys=context_keys, 
            root_directory=self.output_directory, 
            writer_type=self.writer_type
        )

    def process_one_subject(self, sample, idx):
        # Load images
        images = self.input(sample)

        if self.nnunet:
            if not any(isinstance(image, Segmentation) for image in images):
                return {
                    "SampleID": f"{idx:03}",
                    "Error": "No segmentation images found. Skipping sample."
                }

        # Apply transforms to all images
        images = self.transformer(images)

        # Save transformed images
        if self.nnunet:
            metadata = self.output(
                images,
                SampleID=f"{idx:03}",
                SplitType=self.train_test_mapping[idx],
                Dataset=self.dataset_name,
            )
        else: 
            metadata = self.output(images, SampleID=f"{self.input_directory.name}_{idx:03d}") 
        
        metadata["SampleID"] = f"{idx:03d}"

        # Return metadata from each sample
        return metadata

    def run(self):
        # Query Interlacer for samples of desired modalities
        if self.nnunet and not ("SEG" in self.query or "RTSTRUCT" in self.query):
            raise ValueError("nnU-Net requires SEG or RTSTRUCT")
        self.samples = self.lacer.query(self.query)

        # Before processing
        if self.nnunet:
            self.train_test_mapping = create_train_test_mapping(
                list(range(1, len(self.samples)+1)), 
                self.train_size, self.random_state
            )

        # Process the samples in parallel
        self.metadata = Parallel(n_jobs=self.n_jobs)(
            delayed(self.process_one_subject)(sample, idx) for idx, sample in enumerate(self.samples, start=1)
        )

        logger.info(
            f"Finished processing", 
            input_directory=self.input_directory, 
            output_directory=self.output_directory, 
            metadata=self.metadata
        )

        # After processing
        if self.nnunet:
            generate_dataset_json(
                self.output_directory,
                channel_names={
                    channel_num.lstrip('0') or '0': modality 
                    for modality, channel_num in nnUNet_MODALITY_MAP.items() 
                    if modality in self.query.split(",")
                },
                labels={"background": 0, **{name: idx+1 for idx, name in enumerate(self.roi_names)}},
                num_training_cases=sum(1 for file in Path(self.output_directory / "imagesTr").iterdir() if file.is_file()),
                file_ending=self.file_ending,
            )
            create_preprocess_and_train_scripts(self.output_directory, self.dataset_id)

    
def main():
    autopipe = BetaPipeline(
        input_directory=Path("./data"),
        output_directory=Path("./procdata_autobots"),
        query="CT,RTSTRUCT",
        n_jobs=1,
        nnunet=True,
        roi_yaml_path=Path("/home/joshua-siraj/Documents/CDI/IterativeSegNet/configs/roi_yaml_example.yaml"),
        # update_crawl=True,
    )
    autopipe.run()


if __name__ == "__main__":
    main()
