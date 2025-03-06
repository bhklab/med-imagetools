###############################################################
# Example usage:
# python radcure_simple.py ./data/RADCURE/data ./RADCURE_output
###############################################################
from dataclasses import dataclass, field
from pathlib import Path

import click
from joblib import Parallel, delayed  # type: ignore

from imgtools.coretypes import Spacing3D
from imgtools.dicom import Crawler
from imgtools.logging import logger
from imgtools.modalities.interlacer import Interlacer
from imgtools.pipeline import Pipeline
from imgtools.transforms import Resample, Transformer, WindowIntensity


@dataclass
class BetaPipeline(Pipeline):
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
    modalities: list[str] = field(default_factory=lambda: ["CT"])

    # Transformer parameters
    spacing: Spacing3D = field(
        default_factory=lambda: Spacing3D(1.0, 1.0, 0.0)
    )
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
    #     self.lacer = Interlacer()
    #     transforms = [Resample(self.spacing)]

    #     # add W/L adjustment to transforms
    #     if self.window is not None and self.level is not None:
    #         transforms.append(WindowIntensity(self.window, self.level))

    #     self.loader = SampleLoader()
    #     self.saver = SampleSaver(self.output_directory)
    #     self.transformer = Transformer(transforms)

    # def process_one_subject(self, sample):
    #     images = self.loader.load(sample)
    #     transformed_images = self.transform_all(self.transforms, images)
    #     metadata = self.saver.save(transformed_images)
    #     return metadata

    # def run(self):
    #     # JSON/Dictionary of {SeriesUID: {metadata}}
    #     self.db = crawl(self.input_directory)

    #     # List of samples of images [[{seriesuid: 'value', modality: 'value'}, ...]]
    #     self.samples = lacer(self.crawl, self.query)

    #     # Process the gooners
    #     self.metadata = Parallel(n_jobs=self.n_jobs, verbose=self.v)(
    #         delayed(self._process_wrapper)(sample) for sample in self.samples
    #     )


@click.command()
@click.argument(
    "input_directory",
    type=click.Path(
        file_okay=False,
        dir_okay=True,
        writable=True,
        path_type=Path,
        resolve_path=True,
        exists=True,
    ),
    help="Path to the input directory",
)
@click.argument(
    "output_directory",
    type=click.Path(
        file_okay=False,
        dir_okay=True,
        writable=True,
        path_type=Path,
        resolve_path=True,
    ),
    help="Path to the output directory",
)
@click.option(
    "--modalities",
    default="CT",
    type=str,
    help="Modalities to process as a comma separated string",
)
@click.option("--spacing", default=[1.0, 1.0, 0.0], type=tuple)
def main(
    input_directory: Path,
    output_directory: Path,
    modalities: str,
    spacing: tuple,
) -> None:
    logger.debug("Running BetaPipeline via cli with args: %s", locals())

    # paths will be resolved and validated by click params

    # validate modalities
    valid_modalities = ["CT", "MR", "PT", "RTSTRUCT", "RTDOSE", "RTPLAN"]
    mods = set([mod.strip().upper() for mod in modalities.split(",")])
    if not all([mod in valid_modalities for mod in mods]):
        bad_modalities = mods - set(valid_modalities)
        errmsg = (
            "Invalid modalities provided: %s. Valid modalities are: %s"
            % (bad_modalities, valid_modalities)
        )
        logger.error(errmsg)
        raise ValueError(errmsg)

    autopipe = BetaPipeline(
        input_directory=input_directory,
        output_directory=output_directory,
        modalities=list(mods),
        spacing=spacing,
    )
    autopipe.run()


if __name__ == "__main__":
    main()
