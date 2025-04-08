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
GroupBy
    Enum for grouping series by `ReferencedSeriesUID`, `StudyInstanceUID`, or `PatientID`.
    Currently only `ReferencedSeriesUID` is supported.
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
from enum import Enum
from pathlib import Path
from typing import Iterator

import pandas as pd

from imgtools.loggers import logger
from imgtools.utils import OptionalImportError, optional_import, timer

pyvis, _pyvis_available = optional_import("pyvis")

__all__ = ["Interlacer", "GroupBy"]


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
    children: list[SeriesNode] = field(default_factory=list)

    def add_child(self, child_node: SeriesNode) -> None:
        """Add SeriesNode to children"""
        self.children.append(child_node)

    def _get_all_nodes(self) -> list[SeriesNode]:
        """Recursively return all nodes in the tree, including root node and all descendants"""
        all_nodes = [self]  # Start with the current node
        for child in self.children:
            all_nodes.extend(
                child._get_all_nodes()
            )  # Recursively add all nodes from children
        return all_nodes

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

    def __iter__(self) -> Iterator[SeriesNode]:
        """Yield all nodes in the tree"""
        for node in self._get_all_nodes():
            yield node

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


class GroupBy(Enum):
    """
    Enum for fields that reference other fields in the DataFrame.

    ReferencedSeriesUID is the default grouping field,
    which groups series based on their references by building a forest of trees.

    StudyInstanceUID and PatientID are alternatives that can be used when the references are broken or not applicable.
    Here the forest is built by grouping series based on the StudyInstanceUID or PatientID.
    """

    ReferencedSeriesUID = "ReferencedSeriesUID"
    StudyInstanceUID = "StudyInstanceUID"
    PatientID = "PatientID"


class Interlacer:
    """
    Builds and queries a forest of SeriesNode objects from DICOM series data.

    Parameters
    ----------
    crawl_path : str | Path
        Path to the CSV file containing the series data
    group_field : GroupBy, optional
        Field to group series by, by default GroupBy.ReferencedSeriesUID

    Attributes
    ----------
    crawl_df : pd.DataFrame
        DataFrame containing the data loaded from the CSV file
    group_field : GroupBy
        Field used for grouping series
    series_nodes : dict[str, SeriesNode]
        Maps SeriesInstanceUID to SeriesNode objects
    trees : list[list[SeriesNode]] | list[SeriesNode]
        Forest structure containing all series relationships
    root_nodes : list[SeriesNode]
        List of root nodes in the forest
    """

    def __init__(
        self,
        crawl_path: str | Path,
        group_field: GroupBy = GroupBy.ReferencedSeriesUID,
    ) -> None:
        """
        Initializes the Interlacer object.

        Parameters
        ----------
        crawl_path : str or Path
            Path to the CSV file containing the data.
        group_field : GroupBy, optional
            Field to group by, by default GroupBy.ReferencedSeriesUID.
        """
        # Load and drop duplicate SeriesInstanceUID
        self.crawl_path = Path(crawl_path)
        self.crawl_df = pd.read_csv(
            self.crawl_path, index_col="SeriesInstanceUID"
        )
        self.crawl_df = self.crawl_df[
            ~self.crawl_df.index.duplicated(keep="first")
        ]
        self.group_field = group_field

        self.series_nodes: dict[str, SeriesNode] = {}
        self._create_series_nodes()

        self.trees: list[Branch] | list[list[SeriesNode]]
        self.root_nodes: list[SeriesNode] = []

        match group_field:
            case GroupBy.ReferencedSeriesUID:
                self._build_forest()
                self.trees = self._find_branches()
            case GroupBy.StudyInstanceUID:
                logger.warning(
                    "Grouping by StudyInstanceUID. THIS IS IN DEVELOPMENT AND MAY NOT WORK AS EXPECTED."
                )
                self.trees = self._group_by_attribute(
                    list(self.series_nodes.values()), "StudyInstanceUID"
                )
            case GroupBy.PatientID:
                logger.warning(
                    "Grouping by PatientID. THIS IS IN DEVELOPMENT AND MAY NOT WORK AS EXPECTED."
                )
                self.trees = self._group_by_attribute(
                    list(self.series_nodes.values()), "PatientID"
                )
            case _:
                msg = f"Grouping by {group_field} is not supported."
                raise NotImplementedError(msg)

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

        for modality in query:
            if modality in MODALITY_DEPENDENCIES:
                required = MODALITY_DEPENDENCIES[modality]
                if not query_set.intersection(required):
                    msg = f"{modality} requires one of {', '.join(required)}"
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
        if self.group_field != GroupBy.ReferencedSeriesUID:
            msg = f"Querying currently not supported for {self.group_field}"
            raise NotImplementedError(msg)

        queried_modalities = self._get_valid_query(query_string.split(","))
        if not queried_modalities:
            msg = f"Invalid query, {query_string}"
            raise ValueError(msg)

        query_results = self._query(queried_modalities)

        data = [
            [
                {"Series": node.SeriesInstanceUID, "Modality": node.Modality}
                for node in result
            ]
            for result in query_results
        ]

        return data

    def visualize_forest(self, save_path: str | Path | None = None) -> Path:
        """
        Visualize the forest as an interactive network graph.

        Creates an HTML visualization showing nodes for each SeriesNode and
        edges for parent-child relationships.

        Parameters
        ----------
        save_path : str | Path | None, optional
            Path to save the HTML visualization. If None, saves to
            'forest_visualization.html' in crawl file directory.

        Returns
        -------
        Path
            Path to the saved HTML visualization

        Raises
        ------
        OptionalImportError
            If pyvis package is not installed
        NotImplementedError
            If group_field is not GroupBy.ReferencedSeriesUID
        """
        if not _pyvis_available:
            raise OptionalImportError("pyvis")

        if self.group_field != GroupBy.ReferencedSeriesUID:
            raise NotImplementedError(
                "Visualization is only supported when grouping by ReferencedSeriesUID."
            )

        save_path = (
            self.crawl_path.parent / "forest_visualization.html"
            if save_path is None
            else save_path
        )
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


if __name__ == "__main__":
    from rich import print  # noqa
    from imgtools.dicom.crawl import CrawlerSettings, Crawler

    dicom_dir = Path("data")

    crawler_settings = CrawlerSettings(
        dicom_dir=dicom_dir,
        n_jobs=5,
        force=False,
    )

    crawler = Crawler(crawler_settings)

    interlacer = Interlacer(crawler.crawl_results.index_csv_path)
    interlacer.visualize_forest()

    query = "CT,RTSTRUCT"
    samples = interlacer.query(query)

    print(len(samples))