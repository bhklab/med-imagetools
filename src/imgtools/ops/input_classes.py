"""
Input classes refactored to use the BaseInput abstract base class.
"""

from collections import namedtuple
from enum import Enum
import pathlib
import time
from typing import Any, Generator, List, NamedTuple, Optional, Callable
import SimpleITK as sitk
from imgtools.modules import StructureSet, Segmentation, Scan
from dataclasses import dataclass, field
import pandas as pd

from imgtools.crawler import crawl
from imgtools.io.loaders import (
    ImageCSVLoader,
    ImageFileLoader,
    read_dicom_auto,
    read_image,
)
from imgtools.logging import logger
from imgtools.modules.datagraph import DataGraph

from imgtools.ops.base_classes import BaseInput

LoaderFunction = Callable[..., sitk.Image | StructureSet | Segmentation]


def timer(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to measure the execution time of a function and log it with a custom name.

    Args:
        name (str): The custom name to use in the log message.

    Returns:
        Callable[[Callable[..., Any]], Callable[..., Any]]: A decorator that wraps the function to measure its execution time.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            elapsed_time = end_time - start_time
            logger.info(f"{name} took {elapsed_time:.4f} seconds")
            return result

        return wrapper

    return decorator


class ImageMaskModalities(Enum):
    CT_RTSTRUCT = ("CT", "RTSTRUCT")
    CT_SEG = ("CT", "SEG")
    MR_RTSTRUCT = ("MR", "RTSTRUCT")
    MR_SEG = ("MR", "SEG")

    def __str__(self) -> str:
        return f"<{self.value[0]},{self.value[1]}>"


@dataclass
class ImageMaskInput(BaseInput):
    """
    Easily index and load scan-mask pairs.

    This class crawls through the specified 
	directory to index the dataset,
    creates a graph of the dataset, automatically
	querying the graph for image-mask pairs.

    Parameters
    ----------
    dir_path : pathlib.Path
        Path to the directory containing the dataset.
    modalities : ImageMaskModalities
        Modalities to be used for querying the graph.
    n_jobs : int, optional
        Number of jobs to use for crawling, by default -1.
    update_crawl : bool, optional
        Whether to force update the crawl, by default False.
    update_edges : bool, optional
        Whether to force update the edges, by default False.
    imgtools_dir : str, optional
        Directory name for imgtools, by default ".imgtools".
    """

    dir_path: pathlib.Path
    modalities: ImageMaskModalities
    n_jobs: int = -1
    update_crawl: bool = False
    update_edges: bool = False

    imgtools_dir: str = ".imgtools"
    dataset_name: str = field(init=False)
    csv_path: pathlib.Path = field(init=False)
    json_path: pathlib.Path = field(init=False)
    edge_path: pathlib.Path = field(init=False)

    readers: List[LoaderFunction] = field(default_factory=list)
    output_streams: List[str] = field(default_factory=list)
    column_names: List[str] = field(default_factory=list)
    series_names: List[str] = field(default_factory=list)
    modality_list: List[str] = field(default_factory=list)

    graph: DataGraph = field(init=False)

    parsed_df: pd.DataFrame = field(init=False)

    def __post_init__(self) -> None:
        """order of steps summarized

        1. crawl
        2. init graph
        3. parse graph
        4. init loader
        5. create output streams
        """
        self.dataset_name = self.dir_path.name
        create_path = (
            lambda f: self.dir_path.parent
            / self.imgtools_dir
            / f
        )

        self.csv_path = create_path(f"imgtools_{self.dataset_name}.csv")
        self.json_path = create_path(f"imgtools_{self.dataset_name}.json")
        self.edge_path = create_path(f"imgtools_{self.dataset_name}_edges.csv")

        self._crawl()
        self.graph = self._init_graph()

        try:
            self.parsed_df = self.parse_graph(self.modalities)
        except Exception as e:
            errmsg = f"Error parsing the graph: {e}"
            logger.exception(errmsg)
            raise ValueError(errmsg) from e
        parsed_cols = self.parsed_df.columns.tolist()
        for colname in parsed_cols:
            prefix, *rest = colname.split("_")
            match prefix:
                case "folder":
                    self.output_streams.append("_".join(rest))
                    self.column_names.append(colname)
                    self.modality_list.append(rest[0])
                    self.readers.append(read_dicom_auto)
                case "series" if any(
                    modality in rest for modality in self.modalities.value
                ):
                    # we want to check if any of the modalities are the 'rest'
                    # if they are, we want to add the series name to the series_names
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
        rprstring += f"num_cases={len(self)},\n\t"
        rprstring += f"dataset_name='{self.dataset_name}',\n\t"
        rprstring += f"modalities={self.modalities},\n\t"
        rprstring += f"output_streams={self.output_streams},\n\t"
        rprstring += f"series_col_names={self.series_names},\n"
        rprstring += ">"
        return rprstring

    def __len__(self) -> int:
        return len(self.loader)

    @timer("Crawling the dataset")
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
            warnmsg = (
                "The dataset has already been indexed."
                " Use update_crawl to force update."
            )
            logger.warning(warnmsg)

    @timer("Parsing the graph")
    def parse_graph(self, modalities: str | List[str]) -> pd.DataFrame:
        """Parse the graph based on the provided modalities."""
        # lets just assume that the user doesn't pass in a ImageMaskModalities
        # object, but a string or a list of strings
        match modalities:
            case str():
                # probably can do another check to check validity of the string
                modalities = modalities
            case list():
                modalities = ",".join(modalities)
            case ImageMaskModalities():
                modalities = ",".join(modalities.value)
            case _:
                errmsg = f"Modalities must be a string or a list of strings got {type(modalities)}"
                raise ValueError(errmsg)

        logger.info("Querying graph", modality=modalities)
        return self.graph.parser(modalities)

    @timer("Graph initialization")
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
        # return self.loader.get(key)
        ImageMask = namedtuple("ImageMask", ["scan", "mask"])
        case_scan, rtss_or_seg = self.loader.get(key)

        match self.modality_list[1]:
            case "RTSTRUCT":
                # need to convert to Segmentation
                mask = rtss_or_seg.to_segmentation(case_scan)
            case "SEG":
                mask = rtss_or_seg
            case _:
                errmsg = f"Modality {self.modality_list[1]} not recognized."
                raise ValueError(errmsg)

        return ImageMask(case_scan, mask)

    def __getitem__(self, key: str | int) -> object:
        match key:
            case str():
                return self.__call__(key)
            case int():
                if key < len(self):
                    return self.__call__(self.keys()[key])
                errmsg = (
                    f"Index {key} out of range "
                    "Dataset has {len(self)} cases."
                )
                raise IndexError(errmsg)
            case _:
                errmsg = f"Key {type(key)=} must be a str/int"
                raise ValueError(errmsg)


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
    # Define the path to the data
    testdata = pathlib.Path("data")
    # for this tutorial we will use some test image data
    datasets_name = ["NSCLC-Radiomics", "Vestibular-Schwannoma-SEG"]
    vs_seg = ImageMaskInput(
    dir_path=testdata / datasets_name[1],
    modalities=ImageMaskModalities.MR_RTSTRUCT
    )

    nsclsc_rtstruct = ImageMaskInput(
        dir_path=testdata / datasets_name[0],
        modalities=ImageMaskModalities.CT_RTSTRUCT
    )
    nsclsc_seg = ImageMaskInput(
        dir_path=testdata / datasets_name[0],
        modalities=ImageMaskModalities.CT_SEG
    )