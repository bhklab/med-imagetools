"""
Input classes refactored to use the BaseInput abstract base class.
"""

from ast import mod
import pathlib
import time
from typing import Any, Generator, List, Optional, Callable
import SimpleITK as sitk
from imgtools.modules import StructureSet, Segmentation

import pandas as pd

from imgtools.crawler import crawl
from imgtools.io.loaders import (
    BaseLoader,
    ImageCSVLoader,
    ImageFileLoader,
    read_dicom_auto,
    read_image,
    read_dicom_rtstruct,
    read_dicom_scan,
)
from imgtools.logging import logger
from imgtools.modules.datagraph import DataGraph

from imgtools.ops.base_classes import BaseInput

LoaderFunction = Callable[..., sitk.Image | StructureSet | Segmentation]


class ImageMaskInput(BaseInput):
    """ImageMaskInput class for loading and indexing datasets.

    This class crawls through the specified directory to index the dataset,
    creates a graph of the dataset, and allows querying the graph based on modalities.

    After initialization, the user can call the `parse_graph` method to query the graph.

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

    dir_path: pathlib.Path
    dataset_name: str
    n_jobs: int
    update_crawl: bool
    update_edges: bool
    imgtools_dir: str

    csv_path: pathlib.Path
    json_path: pathlib.Path
    edge_path: pathlib.Path

    graph: DataGraph

    parsed_df: pd.DataFrame
    output_streams: List[str]
    column_names: List[str]
    series_names: List[str]
    modalities: List[str]
    readers: List[LoaderFunction]

    def __init__(
        self,
        dir_path: str | pathlib.Path,
        n_jobs: int = -1,
        update_crawl: bool = False,
        update_edges: bool = False,
        imgtools_dir: str = ".imgtools",
        modalities: str | List[str] = "CT,RTSTRUCT",
    ) -> None:
        self.dir_path = pathlib.Path(dir_path)
        self.dataset_name = self.dir_path.name
        self.n_jobs = n_jobs
        self.update_crawl = update_crawl
        self.update_edges = update_edges
        self.imgtools_dir = imgtools_dir

        create_path = (
            lambda file_name: self.dir_path.parent
            / self.imgtools_dir
            / file_name
        )

        self.csv_path = create_path(f"imgtools_{self.dataset_name}.csv")

        self.json_path = create_path(f"imgtools_{self.dataset_name}.json")
        self.edge_path = create_path(f"imgtools_{self.dataset_name}_edges.csv")

        start = time.time()
        self._crawl()
        self.graph = self._init_graph()
        logger.info("Crawl and graph completed", time=time.time() - start)
        start = time.time()
        self.parsed_df = self.parse_graph(modalities)

        parsed_cols: List[str] = self.parsed_df.columns.tolist()

        logger.info("Parsing completed", cols=parsed_cols)

        self.output_streams = []
        self.modalities = []
        self.column_names = []
        self.series_names = []
        self.readers = []

        for colname in parsed_cols:
            # prefix = colname.split("_")
            prefix, *rest = colname.split("_")
            match prefix:
                case "folder":
                    self.output_streams.append("_".join(rest))
                    self.column_names.append(colname)
                    self.modalities.append(rest[0])
                    match rest[0]:
                        case "CT" | "MR" | "RTSTRUCT" | "SEG" | "RTDOSE":
                            self.readers.append(read_dicom_auto)
                        # case "RTSTRUCT":
                        #     self.readers.append(read_dicom_rtstruct)
                        case _:
                            errmsg = f"Unknown modality {rest[0]}"
                            raise ValueError(errmsg)
                case "series":
                    self.series_names.append(colname)
                case _:
                    pass

        logger.info(
            "Parsing completed",
            output_streams=self.output_streams,
            modalities=self.modalities,
            column_names=self.column_names,
            series_names=self.series_names,
            readers=self.readers,
        )

        self.loader = ImageCSVLoader(
            self.parsed_df,
            colnames=self.column_names,
            seriesnames=self.series_names,
            id_column=None,
            expand_paths=False,
            readers=self.readers,
        )

    def keys(self) -> List[str]:
        """Return the keys of the parsed DataFrame."""
        return self.loader.keys()

    def __iter__(self) -> Generator[Any, Any, None]:
        cases = list(self.keys())
        assert len(cases) > 0, "No cases found in the dataset."
        for case in cases:
            yield self.__call__(case)

    def __repr__(self) -> str:
        rprstring = f"ImageMaskInput<\n\t"
        rprstring += f"dataset_name={self.dataset_name},\n\t"
        rprstring += f"output_streams={self.output_streams},\n\t"
        rprstring += f"modalities={self.modalities},\n\t"
        rprstring += f"series_col_names={self.series_names},\n"
        rprstring += ">"
        return rprstring

    def _crawl(self) -> None:
        # CRAWLER
        # -------
        # Checks if dataset has already been indexed
        if not self.csv_path.exists() or self.update_crawl:
            logger.debug("Output exists, force updating.", path=self.csv_path)
            logger.info("Indexing the dataset...")
            crawl(
                top=self.dir_path,
                n_jobs=self.n_jobs,
                csv_path=self.csv_path,
                json_path=self.json_path,
            )
        else:
            logger.warning(
                "The dataset has already been indexed. Use --update to force update."
            )

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
        # modalities = (
        #     modalities if isinstance(modalities, str) else ",".join(modalities)
        # )
        match modalities:
            case str():
                modalities = modalities
            case list():
                modalities = ",".join(modalities)
            case _:
                errmsg = f"Modalities must be a string or a list of strings got {type(modalities)}"
                raise ValueError(errmsg)

        logger.info("Querying graph", modality=modalities)
        return self.graph.parser(modalities)

    def _init_graph(self) -> DataGraph:
        # GRAPH
        # -----
        # Form the graph
        logger.debug("Creating edge path", edge_path=self.edge_path)
        return DataGraph(
            path_crawl=self.csv_path.resolve().as_posix(),
            edge_path=self.edge_path.as_posix(),
            update=self.update_edges,
        )

    def __call__(self, key: object) -> object:
        """Retrieve input data."""
        return self.loader.get(key)


# ruff: noqa
if __name__ == "__main__":  # pragma: no cover
    # Demonstrating usage with mock data
    from pathlib import Path

    datasetindex = Path(
        "/home/jermiah/bhklab/radiomics/repos/med-imagetools/devnotes/notebooks/dicoms"
    )
    # datasetindex = Path(
    #     "/home/jermiah/bhklab/radiomics/repos/readii/tests/4D-Lung"
    # )
    dataset = ImageMaskInput(
        datasetindex,
        modalities="CT,RTSTRUCT,PT",
        update_crawl=False,
        update_edges=True,
    )
    print(dataset)


# TODO: these two are useful, but need some work.
#       Figure out how to best make them useful for the user.


# class ImageCSVInput(BaseInput):
#     """
#     ImageCSVInput class for loading images from a CSV file.

#     Parameters
#     ----------
#     csv_path_or_dataframe : str
#         Path to the CSV file or a pandas DataFrame.

#     colnames : List[str]
#         Column names in the CSV file for image loading.

#     id_column : Optional[str]
#         Column name to use as the subject ID. Default is None.

#     expand_paths : bool
#         Whether to expand relative paths. Default is True.

#     readers : List[Callable]
#         Functions to read images. Default is [read_image].
#     """

#     def __init__(
#         self,
#         csv_path_or_dataframe: str,
#         colnames: List[str],
#         id_column: Optional[str] = None,
#         expand_paths: bool = True,
#         readers: Optional[List] = None,
#     ) -> None:
#         self.csv_path_or_dataframe = csv_path_or_dataframe
#         self.colnames = colnames
#         self.id_column = id_column
#         self.expand_paths = expand_paths
#         self.readers = readers or [read_image]
#         self._loader = ImageCSVLoader(
#             self.csv_path_or_dataframe,
#             colnames=self.colnames,
#             id_column=self.id_column,
#             expand_paths=self.expand_paths,
#             readers=self.readers,
#         )

#     def __call__(self, key: Any) -> Any:  # noqa: ANN401
#         """Retrieve input data."""
#         return self._loader.get(key)
