import click

from imgtools.pipeline import Pipeline
from imgtools.logging import logger
from imgtools.transforms import Resample, WindowIntensity, Transformer

from copy import deepcopy
from joblib import Parallel, delayed

from imgtools.crawler import Crawler

###############################################################
# Example usage:
# python radcure_simple.py ./data/RADCURE/data ./RADCURE_output
###############################################################
from dataclasses import dataclass

@dataclass
class BetaPipeline(Pipeline):
    """
    This pipeline automatically goes through the following steps:
        1. Crawl and connect modalities as samples
        2. Load individual samples
        3. Apply transforms to each image
        4. Save each sample as desired directory structure
    """
    input_directory: str
    output_directory: str
    modalities: str = "CT"
    spacing: tuple = (1., 1., 0.)
    n_jobs: int = -1
    window: float = None
    level: float = None
    # visualize=False,
    # missing_strategy="drop",
    # show_progress=False,
    # warn_on_error=False,
    # overwrite=False,
    # nnunet=False,
    # train_size=1.0,
    # random_state=42,
    # read_yaml_label_names=False,
    # ignore_missing_regex=False,
    # roi_yaml_path="",
    # custom_train_test_split=False,
    # nnunet_inference=False,
    # dataset_json_path="",
    # continue_processing=False,
    # dry_run=False,
    # verbose=False,
    # update=False,
    # roi_select_first=False,
    # roi_separate=False

    def __post_init__(self):
        self.crawl = Crawler()
        self.lacer = Interlacer()
        transforms = [Resample(self.spacing)]

        # add W/L adjustment to transforms
        if self.window is not None and self.level is not None:
            transforms.append(WindowIntensity(self.window, self.level))
        
        self.loader = SampleLoader()
        self.saver  = SampleSaver(self.output_directory)
        self.transformer = Transformer(transforms)

    def process_one_subject(self, sample):
        images             = self.loader.load(sample)
        transformed_images = self.transform_all(self.transforms, images)
        metadata           = self.saver.save(transformed_images)
        return metadata

    def run(self):
        # JSON/Dictionary of {SeriesUID: {metadata}}
        self.db         = crawl(self.input_directory)

        # List of samples of images [[{seriesuid: 'value', modality: 'value'}, ...]]
        self.samples    = lacer(self.crawl, self.query)

        # Process the gooners
        self.metadata   = Parallel(n_jobs=self.n_jobs, verbose=self.v)(
            delayed(self._process_wrapper)(sample) for sample in self.samples
        )


@click.command()
@click.argument("input_directory", type=str, help="Path to the input directory")
@click.argument("output_directory", type=str, help="Path to the output directory")
@click.option("--modalities", default="CT", type=str)
@click.option("--spacing", default=[1., 1., 0.], type=tuple)
def main(input_directory, output_directory, modalities, spacing):
    autopipe = BetaPipeline(input_directory, output_directory, modalities, spacing)
    autopipe.run()

if __name__ == "__main__":
    main()