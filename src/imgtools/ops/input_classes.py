"""
Input classes refactored to use the BaseInput abstract base class.
"""

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
    read_dicom_auto,
)
from imgtools.logging import logger
from imgtools.modules.datagraph import DataGraph

from imgtools.ops.base_classes import BaseInput

LoaderFunction = Callable[..., sitk.Image | StructureSet | Segmentation]


def timer(name: str):
    """Decorator to measure the execution time of a function and log it with a custom name."""

    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
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
    """ImageMaskInput class for loading and indexing datasets.

    This class crawls through the specified directory to index the dataset,
    creates a graph of the dataset, and allows querying the graph based on modalities.

    After initialization, the user can call the `parse_graph` method to query the graph.
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

    def __post_init__(self):
        """order of steps summarized

        1. crawl
        2. init graph
        3. parse graph
        4. init loader
        5. create output streams
        """
        self.dataset_name = self.dir_path.name
        create_path = (
            lambda file_name: self.dir_path.parent
            / self.imgtools_dir
            / file_name
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
            # prefix = colname.split("_")
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
        return self.loader.get(key)

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


# ruff: noqa
if __name__ == "__main__":  # pragma: no cover
    from rich import print

    # Example usage
    print(ImageMaskModalities.CT_RTSTRUCT)  # Output: CT RTSTRUCT
    print(ImageMaskModalities.CT_SEG.value)  # Output: ('CT', 'SEG')
    print(ImageMaskModalities.MR_SEG.value[0])  # Output: MR

    # Demonstrating usage with mock data
    from pathlib import Path

    datasetindex = Path("data/Vestibular-Schwannoma-SEG")
    # datasetindex = Path(
    #     "/home/jermiah/bhklab/radiomics/repos/readii/tests/4D-Lung"
    # )
    dataset = ImageMaskInput(
        datasetindex,
        # modalities=["MR", "RTSTRUCT", "RTDOSE", "RTPLAN"],
        modalities=ImageMaskModalities.MR_RTSTRUCT,
        update_crawl=False,
        update_edges=True,
    )
    print(dataset)
