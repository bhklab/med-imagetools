###############################################################
# Example usage:
# python radcure_simple.py ./data/RADCURE/data ./RADCURE_output
###############################################################
from dataclasses import dataclass, field
from pathlib import Path

from joblib import Parallel, delayed  # type: ignore

from imgtools.coretypes import Spacing3D
from imgtools.dicom import Crawler, Interlacer
from imgtools.transforms import Resample, Transformer, WindowIntensity
from imgtools.io import SampleInput, SampleOutput
from imgtools.dicom.dicom_metadata import MODALITY_TAGS
# from imgtools import Pipeline

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

    n_jobs: int = -1
    dataset_name: str | None = None

    def __post_init__(self) -> None:
        self.crawl = Crawler(
            dicom_dir=self.input_directory,
            n_jobs=self.n_jobs,
            dcm_extension="dcm",
            force=self.update_crawl,
            dataset_name=None, # if you want to rename the .imgtools/{dataset_name} folder
        )
        self.lacer = Interlacer(self.crawl.db_csv) # uses CSV of crawl
        transforms = [Resample(self.spacing)]

        # add W/L adjustment to transforms
        if self.window is not None and self.level is not None:
            transforms.append(WindowIntensity(self.window, self.level))

        context_keys = list(
        set.union(*[MODALITY_TAGS["ALL"], 
                    *[MODALITY_TAGS.get(modality, {}) for modality in self.query.split(",")]]
                )
        )

        self.input = SampleInput(self.crawl.db_json) # uses JSON of crawl
        self.output = SampleOutput(context_keys=context_keys, root_directory=self.output_directory)
        self.transformer = Transformer(transforms)

    def process_one_subject(self, sample, idx):
        # Load images
        images = self.input(sample)

        # Apply transforms to all images
        images = self.transformer(images)

        # Save transformed images
        metadata = self.output(images, SampleID=f"{self.input_directory.name}_{idx:03d}") 

        # Return metadata from each sample
        return metadata

    def run(self):
        # Query Interlacer for samples of desired modalities
        self.samples = self.lacer.query(self.query)

        # Process the samples in parallel
        self.metadata = Parallel(n_jobs=self.n_jobs)(
            delayed(self.process_one_subject)(sample, idx) for idx, sample in enumerate(self.samples, start=1)
        )

    
def main():
    autopipe = BetaPipeline(
        input_directory=Path("./data"),
        output_directory=Path("./procdata_autobots"),
        query="CT,RTSTRUCT",
        spacing=(0.5, 0.5, 0.5),
        # update_crawl=True,
    )
    autopipe.run()


if __name__ == "__main__":
    main()
