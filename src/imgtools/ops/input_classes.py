"""
Input classes refactored to use the BaseInput abstract base class.
"""

import csv
import pathlib
import time
from typing import Any, List, Optional

import pandas as pd

from imgtools.crawler import crawl
from imgtools.io.loaders import (
    ImageCSVLoader,
    ImageFileLoader,
    read_image,
    read_dicom_auto,
)
from imgtools.logging import logger
from imgtools.modules.datagraph import DataGraph

from .base_classes import BaseInput


class ImageAutoInput(BaseInput):
    """ImageAutoInput class is a wrapper class around ImgCSVloader which looks for the specified
    directory and crawls through it as the first step. Using the crawled output data, a graph on
    modalties present in the dataset is formed which stores the relation between all the modalities.
    Based on the user provided modalities, this class loads the information of the user provided modalities

    Parameters
    ----------
    dir_path: str
        Path to dataset top-level directory. The crawler/indexer will start at this directory.

    modalities: str | List[str]
        Either as a list of strings or a single string of comma-separated modalities.
        i.e ["CT", "RTSTRUCT"] or "CT,RTSTRUCT".
        Only samples with ALL modalities will be processed.
        Make sure there are no space between list elements as it is parsed as a string.

    n_jobs: int
        Number of parallel jobs to run when crawling. Default is -1.

    visualize: bool
        Whether to return visualization of the data graph. Requires pyvis to be installed.
        Default is False.

    update: bool
        Whether to update crawled index
    """

    imgtools_dir: str = ".imgtools"

    def __init__(
        self,
        dir_path: str,
        modalities: str | List[str],
        n_jobs: int = -1,
        visualize: bool = False,
        update: bool = False,
    ):
        self.modalities = modalities

        self.dir_path = pathlib.Path(dir_path)
        self.parent = self.dir_path.parent
        self.dataset_name = self.dir_path.name

        self.csv_path = (
            self.parent
            / self.imgtools_dir
            / f"imgtools_{self.dataset_name}.csv"
        )
        self.json_path = (
            self.parent
            / self.imgtools_dir
            / f"imgtools_{self.dataset_name}.json"
        )
        self.edge_path = (
            self.parent
            / self.imgtools_dir
            / f"imgtools_{self.dataset_name}_edges.csv"
        )

        start = time.time()
        # CRAWLER
        # -------
        # Checks if dataset has already been indexed
        if not self.csv_path.exists() or update:
            logger.debug("Output exists, force updating.", path=self.csv_path)
            logger.info("Indexing the dataset...")
            db = crawl(self.dir_path, n_jobs=n_jobs)
            logger.info(f"Number of patients in the dataset: {len(db)}")
        else:
            logger.warning(
                "The dataset has already been indexed. Use --update to force update."
            )

        # GRAPH
        # -----
        # Form the graph
        logger.debug("Creating edge path", edge_path=self.edge_path)
        self.graph = DataGraph(
            path_crawl=self.csv_path.resolve().as_posix(),
            edge_path=self.edge_path.as_posix(),
            visualize=visualize,
            update=update,
        )
        logger.info(
            f"Forming the graph based on the given modalities: {self.modalities}"
        )
        self.df_combined = self.graph.parser(self.modalities)  # type: ignore

        self.output_streams = [
            ("_").join(cols.split("_")[1:])
            for cols in self.df_combined.columns
            if cols.split("_")[0] == "folder"
        ]

        # not sure what this is really doing...

        self.column_names = [
            cols
            for cols in self.df_combined.columns
            if cols.split("_")[0] == "folder"
        ]
        self.series_names = [
            cols
            for cols in self.df_combined.columns
            if cols.split("_")[0] == "series"
        ]
        logger.info(
            f"There are {len(self.df_combined)} cases containing all {self.modalities} modalities."
        )

        self.readers = [
            read_dicom_auto for _ in range(len(self.output_streams))
        ]
        logger.info(f"Total time taken: {time.time() - start:.2f} seconds")
        loader = ImageCSVLoader(
            self.df_combined,
            colnames=self.column_names,
            seriesnames=self.series_names,
            id_column=None,
            expand_paths=False,
            readers=self.readers,
        )

        super().__init__(loader)

    def __call__(self, key: Any) -> Any:  # noqa: ANN001
        """Retrieve input data."""
        return self._loader.get(key)


# TODO: these two are useful, but need some work.
#       Figure out how to best make them useful for the user.


class ImageCSVInput(BaseInput):
    """
    ImageCSVInput class for loading images from a CSV file.

    Parameters
    ----------
    csv_path_or_dataframe : str
        Path to the CSV file or a pandas DataFrame.

    colnames : List[str]
        Column names in the CSV file for image loading.

    id_column : Optional[str]
        Column name to use as the subject ID. Default is None.

    expand_paths : bool
        Whether to expand relative paths. Default is True.

    readers : List[Callable]
        Functions to read images. Default is [read_image].
    """

    def __init__(
        self,
        csv_path_or_dataframe: str,
        colnames: List[str],
        id_column: Optional[str] = None,
        expand_paths: bool = True,
        readers: Optional[List] = None,
    ) -> None:
        self.csv_path_or_dataframe = csv_path_or_dataframe
        self.colnames = colnames
        self.id_column = id_column
        self.expand_paths = expand_paths
        self.readers = readers or [read_image]
        self._loader = ImageCSVLoader(
            self.csv_path_or_dataframe,
            colnames=self.colnames,
            id_column=self.id_column,
            expand_paths=self.expand_paths,
            readers=self.readers,
        )

    def __call__(self, key: Any) -> Any:  # noqa: ANN401
        """Retrieve input data."""
        return self._loader.get(key)


class ImageFileInput(BaseInput):
    """
    ImageFileInput class for loading images from a file directory.

    Parameters
    ----------
    root_directory : str
        Root directory where the image files are stored.

    get_subject_id_from : str
        Method for extracting subject IDs. Options are 'filename' or 'subject_directory'.

    subdir_path : Optional[str]
        Subdirectory path for images. Default is None.

    exclude_paths : List[str]
        List of paths to exclude. Default is an empty list.

    reader : Callable
        Function to read images. Default is `read_image`.
    """

    def __init__(
        self,
        root_directory: str,
        get_subject_id_from: str = "filename",
        subdir_path: Optional[str] = None,
        exclude_paths: Optional[List[str]] = None,
        reader: Optional[Any] = None,  # noqa: ANN401
    ) -> None:
        self.root_directory = root_directory
        self.get_subject_id_from = get_subject_id_from
        self.subdir_path = subdir_path
        self.exclude_paths = exclude_paths or []
        self.reader = reader or read_image
        self._loader = ImageFileLoader(
            self.root_directory,
            get_subject_id_from=self.get_subject_id_from,
            subdir_path=self.subdir_path,
            exclude_paths=self.exclude_paths,
            reader=self.reader,
        )

    def __call__(self, key: Any) -> Any:  # noqa: ANN401
        """Retrieve input data."""
        return self._loader.get(key)


# ruff: noqa
if __name__ == "__main__":  # pragma: no cover
    # Demonstrating usage with mock data
    example_csv_input = ImageCSVInput(
        "path/to/csv", colnames=["image", "label"]
    )
    print("ExampleCSVInput repr:", repr(example_csv_input))

    example_file_input = ImageFileInput("path/to/directory")
    print("ExampleFileInput repr:", repr(example_file_input))
