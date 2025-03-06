from __future__ import annotations

from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Iterator

import pandas as pd

from imgtools.logging import logger
from imgtools.utils import OptionalImportError, optional_import, timer

pyvis, _pyvis_available = optional_import("pyvis")


class SeriesNode:
    """
    A node in the series tree representing a DICOM series.

    Parameters
    ----------
    series : str
        The SeriesInstanceUID of this node
    row : pd.Series
        A pandas Series containing metadata for this series

    Attributes
    ----------
    Series : str
        The SeriesInstanceUID
    Modality : str
        The DICOM modality type
    PatientID : str
        The patient identifier
    StudyInstanceUID : str
        The study instance identifier
    children : list[SeriesNode]
        Child nodes representing referenced series
    """

    def __init__(self, series: str, row: pd.Series) -> None:
        self.Series = series
        self.Modality = row.Modality
        self.PatientID = row.PatientID
        self.StudyInstanceUID = row.StudyInstanceUID

        self.children: list[SeriesNode] = []

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
            return self.Series == other
        return isinstance(other, SeriesNode) and self.Series == other.Series

    def __iter__(self) -> Iterator[SeriesNode]:
        """Yield all nodes in the tree"""
        for node in self._get_all_nodes():
            yield node

    def __repr__(self, level: int = 0) -> str:
        """Recursive representation of the tree structure"""
        indent = "  " * level
        result = f"{indent}- {self.Modality}, (SERIES: {self.Series})\n"
        for child in self.children:
            result += child.__repr__(level + 1)
        return result


class Branch:
    """
    Represents a unique path (branch) in the forest.

    Parameters
    ----------
    series_nodes : list[SeriesNode] | None, optional
        List of SeriesNode objects in this branch, by default None

    Attributes
    ----------
    series_nodes : list[SeriesNode]
        The nodes making up this branch
    """

    def __init__(self, series_nodes: list[SeriesNode] | None = None) -> None:
        self.series_nodes = [] if series_nodes is None else series_nodes

    def add_node(self, node: SeriesNode) -> None:
        """Add a SeriesNode to the branch."""
        self.series_nodes.append(node)

    def get_modality_map(self) -> dict[str, SeriesNode]:
        """Returns a dictionary mapping Modality to SeriesNode."""
        return {node.Modality: node for node in self.series_nodes}

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
    query_branches : bool, optional
        If True, queries all branches as different samples. Only applies when
        grouping by ReferencedSeriesUID. Default is False.

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
    query_branches : bool
        Whether to query all branches as different samples
    """

    def __init__(
        self,
        crawl_path: str | Path,
        group_field: GroupBy = GroupBy.ReferencedSeriesUID,
        query_branches: bool = False,
    ) -> None:
        """
        Initializes the Interlacer object.

        Parameters
        ----------
        crawl_path : str or Path
            Path to the CSV file containing the data.
        group_field : GroupBy, optional
            Field to group by, by default GroupBy.ReferencedSeriesUID.
        query_branches : bool, optional, default=False
            If True, queries all branches as different samples
            (Only applicable when grouping by ReferencedSeriesUID).
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
        self.query_branches = query_branches
        if (
            self.query_branches
            and self.group_field != GroupBy.ReferencedSeriesUID
        ):
            logger.warning(
                "ingoring query_branches as it is only applicable when grouping by ReferencedSeriesUID",
                query_branches=self.query_branches,
                group_field=self.group_field,
            )

        self.series_nodes: dict[str, SeriesNode] = {}
        self._create_series_nodes()

        self.trees: list[list[SeriesNode]] | list[SeriesNode]
        self.root_nodes: list[SeriesNode] = []

        match group_field:
            case GroupBy.ReferencedSeriesUID:
                self._build_forest()
                self.trees = (
                    self._find_branches()
                    if self.query_branches
                    else self.root_nodes
                )
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
                series_instance_uid, row.astype(str)
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
            branch.append(node)
            if node.children:
                for child in node.children:
                    traverse_tree(child, branch.copy())
            else:
                branches.append(Branch(branch))

        for root in self.root_nodes:
            traverse_tree(root, [])

        return branches

    def _query(self, queried_modalities: set[str]) -> list[list[SeriesNode]]:
        """Returns samples that contain *all* specified modalities."""
        result = []

        for tree in self.trees:
            series_nodes = [
                node for node in tree if node.Modality in queried_modalities
            ]
            present_modalities = {node.Modality for node in series_nodes}
            if queried_modalities <= present_modalities:
                result.append(series_nodes)

        return result

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
        query_results = self._query(set(query_string.split(",")))

        data = [
            [
                {"Series": node.Series, "Modality": node.Modality}
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
            title = f"PatientID: {node.PatientID}\nSeries: {node.Series}"
            net.add_node(
                node.Series, label=node.Modality, title=title, color=color
            )
            if parent:
                net.add_edge(node.Series, parent.Series)

            for child in node.children:
                add_node_and_edges(child, node)

        # Add root nodes (each representing a patient)
        for root in self.root_nodes:
            add_node_and_edges(root)
            patient_trees[root.PatientID] = (
                root.Series
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
            }
            #sidebar h2 {
                text-align: center;
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
            }
            #sidebar a:hover {
                text-decoration: underline;
            }
        </style>
        <script>
            function focusNode(nodeId) {
                network.selectNodes([nodeId]); 
                network.focus(nodeId, { scale: 3.5, animation: true });
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

    interlacer = Interlacer("testdata/.imgtools/Head-Neck-PET-CT/crawldb.csv")
    interlacer.visualize_forest()
    # result = interlacer.query("CT,RTSTRUCT")

    # print(result)
