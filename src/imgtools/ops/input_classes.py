"""
Input classes refactored to use the BaseInput abstract base class.
"""

import pathlib
import time
from typing import Any, List, Optional

import pandas as pd

from imgtools.crawler import crawl
from imgtools.io.loaders import (
    ImageCSVLoader,
    ImageFileLoader,
    read_image,
)
from imgtools.logging import logger
from imgtools.modules.datagraph import DataGraph

from .base_classes import BaseInput


class CrawlGraphInput(BaseInput):
    """CrawlGraphInput class for loading and indexing datasets.

    This class crawls through the specified directory to index the dataset,
    creates a graph of the dataset, and allows querying the graph based on modalities.

    Parameters
    ----------
    dir_path : str | pathlib.Path
        Path to the dataset's top-level directory. The crawler/indexer will start at this directory.

    n_jobs : int
        Number of parallel jobs to run when crawling. Default is -1.

    update_crawl : bool
        Whether to update the crawled index. Default is False.

    imgtools_dir : str
        Directory name for imgtools output files. Default is ".imgtools".

    db : dict
        Dictionary containing the indexed dataset, created by the crawler.

    graph : DataGraph
        DataGraph object containing the dataset graph.
    """

    dir_path: str
    n_jobs: int
    update_crawl: bool
    imgtools_dir: str

    db: dict
    graph: DataGraph

    def __init__(
        self,
        dir_path: str | pathlib.Path,
        n_jobs: int = -1,
        update_crawl: bool = False,
        imgtools_dir: str = ".imgtools",
    ) -> None:
        self.dir_path = pathlib.Path(dir_path)
        self.dataset_name = self.dir_path.name
        self.n_jobs = n_jobs
        self.update_crawl = update_crawl
        self.imgtools_dir = imgtools_dir

        self.csv_path = self._create_path(f"imgtools_{self.dataset_name}.csv")
        self.json_path = self._create_path(
            f"imgtools_{self.dataset_name}.json"
        )
        self.edge_path = self._create_path(
            f"imgtools_{self.dataset_name}_edges.csv"
        )

        start = time.time()
        self.db = self._crawl()
        self.graph = self._init_graph()

        logger.info("Crawl and graph completed", time=time.time() - start)

    def _create_path(self, file_name: str) -> pathlib.Path:
        """Helper function to create paths.

        TODO: would be nice to allow users to specify this better
        """
        return self.dir_path.parent / self.imgtools_dir / file_name

    def _crawl(self) -> dict:
        # CRAWLER
        # -------
        # Checks if dataset has already been indexed
        if not self.csv_path.exists() or self.update:
            logger.debug("Output exists, force updating.", path=self.csv_path)
            logger.info("Indexing the dataset...")
            db = crawl(
                top=self.dir_path,
                n_jobs=self.n_jobs,
                csv_path=self.csv_path,
                json_path=self.json_path,
            )
            logger.info(f"Number of patients in the dataset: {len(db)}")
        else:
            logger.warning(
                "The dataset has already been indexed. Use --update to force update."
            )
        return db

    def parse_graph(self, modalities: str | List[str]) -> pd.DataFrame:
        """Parse the graph based on the provided modalities.

        TODO: establish how users can use the df columns to filter the data.

        Parameters
        ----------
        modalities : str | List[str]
            Either a list of strings or a single string of comma-separated modalities.
            For example, ["CT", "RTSTRUCT"] or "CT,RTSTRUCT".
            Only samples with ALL specified modalities will be processed.
            Ensure there are no spaces between list elements if provided as a string.

        Returns
        -------
        pd.DataFrame
            A pandas DataFrame containing the parsed graph.
        """
        assert self.graph is not None, "Graph not initialized."
        modalities = (
            modalities if isinstance(modalities, str) else ",".join(modalities)
        )
        logger.info("Querying graph", modality=modalities)
        self.df_combined = self.graph.parser(modalities)
        return self.df_combined

    def _init_graph(self) -> DataGraph:
        # GRAPH
        # -----
        # Form the graph
        logger.debug("Creating edge path", edge_path=self.edge_path)
        return DataGraph(
            path_crawl=self.csv_path.resolve().as_posix(),
            edge_path=self.edge_path.as_posix(),
            update=self.update_crawl,
        )

    def __call__(self, key: object) -> object:
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
