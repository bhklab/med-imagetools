"""
Interlacer Module

This module defines the `Interlacer` class, which constructs and queries a hierarchical
forest of DICOM series based on their metadata relationships. It enables efficient
grouping, querying, and visualization of medical imaging series.

Classes
-------
SeriesNode
    Represents an individual DICOM series and its hierarchical relationships.
Branch
    Represents a path within the hierarchy, maintaining ordered modality sequences.
Interlacer
    Builds the hierarchy, processes queries, and visualizes the relationships.

Examples
--------
>>> from pathlib import Path
>>> from rich import print  # noqa
>>> from imgtools.dicom.crawl import (
...     CrawlerSettings,
...     Crawler,
... )
>>> from imgtools.dicom.interlacer import Interlacer
>>> dicom_dir = Path("data")
>>> crawler_settings = CrawlerSettings(
>>>     dicom_dir=dicom_dir,
>>>     n_jobs=12,
>>>     force=False
>>> )
>>> crawler = Crawler.from_settings(crawler_settings)
>>> interlacer = Interlacer(crawler.db_csv)
>>> interlacer.visualize_forest()
>>> query = "CT,RTSTRUCT"
>>> samples = interlacer.query(query)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import pandas as pd
from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.theme import Theme
from rich.tree import Tree as RichTree

from imgtools.loggers import logger
from imgtools.utils import OptionalImportError, optional_import, timer

pyvis, _pyvis_available = optional_import("pyvis")

__all__ = ["Interlacer"]


@dataclass
class SeriesNode:
    """
    A node in the series tree representing a DICOM series.

    Parameters
    ----------
    SeriesInstanceUID : str
        The SeriesInstanceUID of this node
    Modality : str
        The DICOM modality type
    PatientID : str
        The patient identifier
    StudyInstanceUID : str
        The study instance identifier
    children : list[SeriesNode]
        Child nodes representing referenced series
    """

    SeriesInstanceUID: str
    Modality: str
    PatientID: str
    StudyInstanceUID: str
    folder: str
    children: list[SeriesNode] = field(default_factory=list)

    def add_child(self, child_node: SeriesNode) -> None:
        """Add SeriesNode to children"""
        self.children.append(child_node)

    def __eq__(self, other: object) -> bool:
        """Equality check based on index"""
        if isinstance(other, str):  # Direct index check
            return self.SeriesInstanceUID == other
        return (
            isinstance(other, SeriesNode)
            and self.SeriesInstanceUID == other.SeriesInstanceUID
        )

    def __hash__(self) -> int:
        return hash(self.SeriesInstanceUID)

    def __repr__(self, level: int = 0) -> str:
        """Recursive representation of the tree structure"""
        indent = "  " * level
        result = (
            f"{indent}- {self.Modality}, (SERIES: {self.SeriesInstanceUID})\n"
        )
        for child in self.children:
            result += child.__repr__(level + 1)
        return result

    @classmethod
    def copy_node(cls, node: SeriesNode) -> SeriesNode:
        return cls(
            node.SeriesInstanceUID,
            node.Modality,
            node.PatientID,
            node.StudyInstanceUID,
            node.folder,
        )


@dataclass
class Branch:
    """
    Represents a unique path (branch) in the forest.

    Parameters
    ----------
    series_nodes : list[SeriesNode]
        List of SeriesNode objects in this branch

    Attributes
    ----------
    series_nodes : list[SeriesNode]
        The nodes making up this branch
    """

    series_nodes: list[SeriesNode] = field(default_factory=list)

    def add_node(self, node: SeriesNode) -> None:
        """Add a SeriesNode to the branch."""
        self.series_nodes.append(node)

    def check_branch(self, query: list[str]) -> list[SeriesNode]:
        """Check if the given query is a sub-sequence and has the same order as the nodes in the branch."""
        node_mode = [node.Modality for node in self.series_nodes]

        if query == [
            "CT",
            "RTSTRUCT",
        ]:  # EXCEPTION: Avoid PT in between CT and RTSTRUCT
            return next(
                (
                    self.series_nodes[idx : idx + 2]
                    for idx in range(len(self.series_nodes) - 1)
                    if node_mode[idx : idx + 2] == query
                ),
                [],
            )

        elif all(item in node_mode for item in query):
            return [
                node for node in self.series_nodes if node.Modality in query
            ]

        else:
            return []

    def __iter__(self) -> Iterator[SeriesNode]:
        """Yield the node from each SeriesNode in the branch."""
        for node in self.series_nodes:
            yield node

    def __repr__(self) -> str:
        """Return a string representation of the branch."""
        return " -> ".join(node.Modality for node in self.series_nodes)


@dataclass
class Interlacer:
    """
    Builds and queries a forest of SeriesNode objects from DICOM series data.

    Parameters
    ----------
    crawl_index : str | Path | pd.DataFrame
        Path to the CSV file or DataFrame containing the series data

    Attributes
    ----------
    crawl_df : pd.DataFrame
        DataFrame containing the data loaded from the CSV file or passed in `crawl_index`
    series_nodes : dict[str, SeriesNode]
        Maps SeriesInstanceUID to SeriesNode objects
    trees : list[Branch]
        Forest structure containing all series relationships as branches
    root_nodes : list[SeriesNode]
        List of root nodes in the forest
    """

    crawl_index: str | Path | pd.DataFrame
    crawl_df: pd.DataFrame = field(init=False)
    series_nodes: dict[str, SeriesNode] = field(
        default_factory=dict, init=False
    )
    trees: list[Branch] = field(default_factory=list, init=False)
    root_nodes: list[SeriesNode] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        """Initialize the Interlacer after dataclass initialization."""
        if isinstance(self.crawl_index, (str, Path)):
            self.crawl_df = pd.read_csv(
                self.crawl_index, index_col="SeriesInstanceUID"
            )
        elif isinstance(self.crawl_index, pd.DataFrame):
            self.crawl_df = self.crawl_index.copy()
            self.crawl_df.set_index(
                "SeriesInstanceUID",
                inplace=True,
            )
        else:
            errmsg = f"Invalid type for crawl_index: {type(self.crawl_index)}"
            raise TypeError(errmsg)

        self.crawl_df = self.crawl_df[
            ~self.crawl_df.index.duplicated(keep="first")
        ]

        self._create_series_nodes()
        self._build_forest()
        self.trees = self._find_branches()

    def _group_by_attribute(
        self, items: list[SeriesNode], attribute: str
    ) -> list[list[SeriesNode]]:
        """
        Groups SeriesNode items by a specific attribute.

        Parameters
        ----------
        items : list[SeriesNode]
            List of SeriesNode objects to group
        attribute : str
            Name of the attribute to group by

        Returns
        -------
        list[list[SeriesNode]]
            Lists of SeriesNodes grouped by the attribute
        """
        grouped_dict = defaultdict(list)
        for item in items:
            grouped_dict[getattr(item, attribute)].append(item)
        return list(grouped_dict.values())

    def _create_series_nodes(self) -> None:
        """Creates a SeriesNode object for each row in the DataFrame."""
        for index, row in self.crawl_df.iterrows():
            series_instance_uid = str(index)
            self.series_nodes[series_instance_uid] = SeriesNode(
                series_instance_uid,
                row.Modality,
                row.PatientID,
                row.StudyInstanceUID,
                row.folder,
            )

    @timer("Building forest based on references")
    def _build_forest(self) -> None:
        """
        Constructs a forest of trees from the DataFrame by
        defining parent-child relationships using ReferenceSeriesUID.
        """
        for index, row in self.crawl_df.iterrows():
            series_instance_uid = str(index)
            modality = row.Modality
            reference_series_uid = row.ReferencedSeriesUID

            node = self.series_nodes[series_instance_uid]

            if modality in ["CT", "MR"] or (
                modality == "PT" and pd.isna(reference_series_uid)
            ):
                self.root_nodes.append(node)

            if (
                pd.notna(reference_series_uid)
                and reference_series_uid in self.series_nodes
            ):
                parent_node = self.series_nodes[reference_series_uid]
                parent_node.add_child(node)

    @timer("Finding individual branches of tree")
    def _find_branches(self) -> list[Branch]:
        """
        Finds and records all branches in the forest
        using depth-first search (DFS).
        """
        branches: list[Branch] = []

        def traverse_tree(node: SeriesNode, branch: list[SeriesNode]) -> None:
            branch.append(SeriesNode.copy_node(node))
            if node.children:
                for child in node.children:
                    traverse_tree(child, branch.copy())
            else:
                branches.append(Branch(branch))

        for root in self.root_nodes:
            traverse_tree(root, [])

        return branches

    def _get_valid_query(self, query: list[str]) -> list[str]:
        """
        Validates the query based on the following rules:

        Notes
        -----
        Rules:
            1. RTSTRUCT and RTDOSE require CT, MR, or PT.
            2. SEG requires CT or MR.
        Example:
            "CT,RTDOSE" is valid.
            "CT,MR,RTSTRUCT" is valid.
            "CT,PT,RTSTRUCT" is valid.
            "PT,SEG" is invalid.
            "RTSTRUCT,RTDOSE" is invalid.
        """

        MODALITY_DEPENDENCIES: dict[str, set[str]] = {  # noqa: N806
            "RTSTRUCT": {"CT", "MR", "PT"},
            "RTDOSE": {"CT", "MR", "PT"},
            "SEG": {"CT", "MR"},
        }

        valid_order = ["CT", "MR", "PT", "SEG", "RTSTRUCT", "RTDOSE"]
        query_set = set(query)

        if not query_set.issubset(set(valid_order)):
            msg = (
                f"Invalid query: ({', '.join(query)}), "
                f"provided modalities: [{', '.join(query_set - set(valid_order))}] "
                f"are not supported, "
                f"supported modalities: {', '.join(valid_order)}"
            )
            raise ValueError(msg)

        for modality in query:
            if modality in MODALITY_DEPENDENCIES:
                required = MODALITY_DEPENDENCIES[modality]
                if not query_set.intersection(required):
                    msg = f"Invalid query: ({', '.join(query)}), {modality} requires one of {', '.join(required)}"
                    raise ValueError(msg)

        return [modality for modality in valid_order if modality in query_set]

    def _query(self, queried_modalities: list[str]) -> list[list[SeriesNode]]:
        """Returns samples that contain *all* specified modalities."""
        results = []
        seen_result = set()

        # Step 1: Query each tree(Branch)
        for tree in self.trees:
            assert isinstance(
                tree, Branch
            )  # To be updated, when supporting other grouping
            query_result = tree.check_branch(queried_modalities)
            if query_result and not tuple(query_result) in seen_result:
                results.append(query_result)
                seen_result.add(tuple(query_result))

        # Step 2: Group results by root node
        grouped_results: dict[SeriesNode, list[SeriesNode]] = defaultdict(list)
        for result in results:
            root_node = result[0]
            if not grouped_results[root_node]:
                grouped_results[root_node].append(root_node)

            for node in result[1:]:
                if node not in grouped_results[root_node]:
                    grouped_results[root_node].append(node)

        return list(grouped_results.values())

    @timer("Querying forest")
    def query(self, query_string: str) -> list[list[dict[str, str]]]:
        """
        Query the forest for specific modalities.

        Parameters
        ----------
        query_string : str
            Comma-separated string of modalities to query (e.g., 'CT,MR')

        Returns
        -------
        list[list[dict[str, str]]]
            List of matched series groups where each series is represented by a
            dict containing 'Series' and 'Modality' keys

        Notes
        -----
        Supported modalities:
        - CT: Computed Tomography
        - PT: Positron Emission Tomography
        - MR: Magnetic Resonance Imaging
        - SEG: Segmentation
        - RTSTRUCT: Radiotherapy Structure
        - RTDOSE: Radiotherapy Dose
        """
        queried_modalities = self._get_valid_query(query_string.split(","))
        query_results = self._query(queried_modalities)

        data = [
            [
                {"Series": node.SeriesInstanceUID, "Modality": node.Modality}
                for node in result
            ]
            for result in query_results
        ]

        return data

    def visualize_forest(self, save_path: str | Path) -> Path:
        """
        Visualize the forest as an interactive network graph.

        Creates an HTML visualization showing nodes for each SeriesNode and
        edges for parent-child relationships.

        Parameters
        ----------
        save_path : str | Path
            Path to save the HTML visualization.

        Returns
        -------
        Path
            Path to the saved HTML visualization

        Raises
        ------
        OptionalImportError
            If pyvis package is not installed
        """
        if not _pyvis_available:
            raise OptionalImportError("pyvis")

        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        net = pyvis.network.Network(
            height="800px", width="100%", notebook=False, directed=True
        )

        modality_colors = {
            "CT": "#1f77b4",  # Blue
            "MR": "#ff7f0e",  # Orange
            "PT": "#2ca02c",  # Green
            "SEG": "#d62728",  # Red
            "RTSTRUCT": "#9467bd",  # Purple
            "RTPLAN": "#8c564b",  # Brown
            "RTDOSE": "#e377c2",  # Pink
        }

        patient_trees = {}  # Store patient-to-root mappings

        def add_node_and_edges(
            node: SeriesNode, parent: SeriesNode | None = None
        ) -> None:
            color = modality_colors.get(
                node.Modality, "#7f7f7f"
            )  # Default gray if unknown
            title = f"PatientID: {node.PatientID}\nSeries: {node.SeriesInstanceUID}"
            net.add_node(
                node.SeriesInstanceUID,
                label=node.Modality,
                title=title,
                color=color,
            )
            if parent:
                net.add_edge(node.SeriesInstanceUID, parent.SeriesInstanceUID)

            for child in node.children:
                add_node_and_edges(child, node)

        # Add root nodes (each representing a patient)
        for root in self.root_nodes:
            add_node_and_edges(root)
            patient_trees[root.PatientID] = (
                root.SeriesInstanceUID
            )  # Store the root Series as entry point for the patient

        net.force_atlas_2based()

        # Generate the sidebar HTML with clickable patient IDs
        sidebar_html = """
        <div id="sidebar">
            <h2>Patient List</h2>
            <ul>
        """
        for patient_id, root_series in patient_trees.items():
            sidebar_html += f'<li><a href="#" onclick="focusNode(\'{root_series}\')">{patient_id}</a></li>'

        sidebar_html += """
            </ul>
        </div>

        <style>
            body {
                margin: 0;
                padding: 0;
            }

            #sidebar {
                position: fixed;
                left: 0;
                top: 0;
                width: 250px;
                height: 100%;
                background: #f4f4f4;
                padding: 20px;
                overflow-y: auto;
                box-shadow: 2px 0 5px rgba(0,0,0,0.3);
                z-index: 1000;
            }

            #sidebar h2 {
                text-align: center;
                font-family: Arial, sans-serif;
            }

            #sidebar ul {
                list-style: none;
                padding: 0;
            }

            #sidebar li {
                margin: 10px 0;
            }

            #sidebar a {
                text-decoration: none;
                color: #007bff;
                font-weight: bold;
                font-family: Arial, sans-serif;
            }

            #sidebar a:hover {
                text-decoration: underline;
            }

            #mynetwork {
                margin-left: 270px; /* Room for sidebar */
                height: 100vh;
            }
        </style>

        <script type="text/javascript">
            function focusNode(nodeId) {
                if (typeof network !== 'undefined') {
                    network.selectNodes([nodeId]);
                    network.focus(nodeId, {
                        scale: 3.5,
                        animation: {
                            duration: 500,
                            easingFunction: "easeInOutQuad"
                        }
                    });
                } else {
                    alert("Network graph not loaded yet.");
                }
            }
        </script>
        """

        # Generate the full HTML file
        logger.info("Saving forest visualization...", path=save_path)
        net_html = net.generate_html()
        full_html = net_html.replace(
            "<body>", f"<body>{sidebar_html}"
        )  # Insert sidebar into HTML

        # Write the final HTML file
        save_path.write_text(full_html, encoding="utf-8")

        return save_path

    def print_tree(self, input_directory: Path | None) -> None:
        """Print a representation of the forest."""
        print_interlacer_tree(self.root_nodes, input_directory)


class ModalityHighlighter(RegexHighlighter):
    """Highlights DICOM modality tags using custom styles."""

    base_style = "modality."
    highlights = [
        r"(?P<CT>\bCT\b)",
        r"(?P<MR>\bMR\b)",
        r"(?P<PT>\bPT\b)",
        r"(?P<SEG>\bSEG\b)",
        r"(?P<RTSTRUCT>\bRTSTRUCT\b)",
        r"(?P<RTPLAN>\bRTPLAN\b)",
        r"(?P<RTDOSE>\bRTDOSE\b)",
    ]

    modality_theme = Theme(
        {
            "modality.CT": "bold blue",
            "modality.MR": "bold dark_orange",
            "modality.PT": "bold green3",
            "modality.SEG": "bold red",
            "modality.RTSTRUCT": "bold medium_purple",
            "modality.RTPLAN": "bold tan",
            "modality.RTDOSE": "bold pink1",
        }
    )


def print_interlacer_tree(
    root_nodes: list[SeriesNode], input_directory: Path | None
) -> None:
    from collections import defaultdict

    from imgtools.utils import truncate_uid

    console = Console(
        highlighter=ModalityHighlighter(),
        theme=ModalityHighlighter.modality_theme,
    )
    root_tree = RichTree(
        "[bold underline]Patients[/bold underline]", highlight=True
    )

    def add_series_node(node: SeriesNode, branch: RichTree) -> None:
        left_part = f"{node.Modality} (Series-{truncate_uid(node.SeriesInstanceUID, last_digits=8)})"
        if input_directory:
            folder = Path(input_directory).parent / node.folder
            folder = folder.resolve()
        else:
            folder = Path(node.folder).resolve()

        if folder.exists():
            folder_str = f"\t\t[dim]{str(folder.relative_to(Path().cwd()))}[/]"
            left_part += folder_str

        child_branch = branch.add(left_part, highlight=True)
        for child in node.children:
            add_series_node(child, child_branch)

    patient_groups: dict[str, list[SeriesNode]] = defaultdict(list)
    for root in root_nodes:
        patient_groups[root.PatientID].append(root)

    # sort the patient groups by PatientID
    patient_groups = dict(
        sorted(patient_groups.items(), key=lambda item: item[0])
    )

    for patient_id, roots in patient_groups.items():
        patient_branch = root_tree.add(f"[blue bold]{patient_id}[/]")
        for root in roots:
            add_series_node(root, patient_branch)

    console.print(root_tree, highlight=True)


if __name__ == "__main__":
    from rich import print  # noqa
    from imgtools.dicom.crawl import CrawlerSettings, Crawler

    dicom_dirs = [
        Path("data/Vestibular-Schwannoma-SEG"),
        # Path("data/NSCLC_Radiogenomics"),
        # Path("data/Head-Neck-PET-CT"),
    ]
    interlacers = []
    for directory in dicom_dirs:
        crawler_settings = CrawlerSettings(
            dicom_dir=directory,
            n_jobs=5,
            force=False,
        )

        crawler = Crawler(crawler_settings)
        interlacer = Interlacer(crawler.index)
        interlacers.append(interlacer)
        # interlacer.visualize_forest(
        #     directory.parent.parent / directory.name / "interlacer.html"
        # )
        print(f"Query Result {interlacer.query('MR,RTSTRUCT')}")

    for interlacer, input_dir in zip(interlacers, dicom_dirs):
        interlacer.print_tree(input_dir)
