from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

from imgtools.config.configuration import MedImageToolsSettings
from imgtools.transforms import (
    BaseTransform,
    Resample,
    Transformer,
    WindowIntensity,
)

if TYPE_CHECKING:
    from imgtools.coretypes.base_masks import VectorMask
    from imgtools.coretypes.base_medimage import MedImage
    from imgtools.dicom.interlacer import SeriesNode
    from imgtools.io.sample_input import SampleInput
    from imgtools.io.sample_output import SampleOutput


@dataclass
class DeltaPipeline:
    """
    This pipeline automatically goes through the following steps:
        1. Crawl and connect modalities as samples
        2. Load individual samples
        3. Apply transforms to each image
        4. Save each sample as desired directory structure
    """

    input: SampleInput
    output: SampleOutput

    # for now only supporting input and output from yaml file

    # Interlacer parameters
    query: str = "CT,RTSTRUCT"

    # Transformer parameters
    spacing: tuple[float, float, float] = (1.0, 1.0, 0.0)
    window: float | None = None
    level: float | None = None

    @classmethod
    def from_user_yaml(cls, path: Path) -> DeltaPipeline:
        """
        Load a pipeline from a YAML file.
        Currently only supports input and output, transformer to be added.
        """
        settings = MedImageToolsSettings.from_user_yaml(path)
        return cls(
            input=settings.input,
            output=settings.output,
        )

    def __post_init__(self) -> None:
        """
        Post-initialization to set up the pipeline.
        """
        transforms: list[BaseTransform]
        transforms = [
            Resample(
                self.spacing,
                interpolation="linear",
                anti_alias=True,
                anti_alias_sigma=None,
                transform=None,
                output_size=None,
            ),
        ]

        if self.window is not None and self.level is not None:
            transforms.append(
                WindowIntensity(window=self.window, level=self.level)
            )

        self.transformer = Transformer(transforms)

    def process_one_sample(self, sample: list[SeriesNode]) -> None:
        """
        Process a single sample.
        """
        # Load the sample
        sample_images: Sequence[MedImage | VectorMask] = (
            self.input.load_sample(sample)
        )

        transformed_images = self.transformer(sample_images)

        for image in transformed_images:
            print(image)


if __name__ == "__main__":
    from rich import print  # noqa: A004

    pipeline = DeltaPipeline.from_user_yaml(Path("imgtools.yaml"))

    print(pipeline)
    pipeline.process_one_sample(pipeline.input.query("CT,RTSTRUCT")[0])
