"""
Interlacer Module

This module defines the `Interlacer` class, which constructs and queries a hierarchical
forest of DICOM series based on their metadata relationships. It enables efficient
grouping, querying, and visualization of medical imaging series.

The Interlacer provides tools for analyzing complex DICOM relationships, such as
connections between different imaging modalities (CT, MR, PT) and derived objects
(RTSTRUCT, RTDOSE, SEG). It enables validation of relationships based on DICOM
standards and medical imaging workflows.

Classes
-------
SeriesNode
    Represents an individual DICOM series and its hierarchical relationships.
Interlacer
    Builds the hierarchy, processes queries, and visualizes the relationships.
InterlacerQueryError
    Base exception for query validation errors.
UnsupportedModalityError
    Raised when an unsupported modality is specified in a query.
MissingDependencyModalityError
    Raised when modalities in a query are missing required dependencies.
ModalityHighlighter
    Rich text highlighter for pretty-printing DICOM modalities.

Features
--------
- Hierarchical representation of DICOM relationships
- Query for specific combinations of modalities with dependency validation
- Interactive visualization of DICOM series relationships
- Rich text console display of patient/series hierarchies
- Validation of modality dependencies based on DICOM standards
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.theme import Theme
from rich.tree import Tree as RichTree

from imgtools.loggers import logger
from imgtools.utils import OptionalImportError, optional_import

pyvis, _pyvis_available = optional_import("pyvis")

__all__ = ["Interlacer"]


class InterlacerQueryError(Exception):
    """Base exception for Interlacer query errors."""

    pass


class UnsupportedModalityError(InterlacerQueryError):
    """Raised when an unsupported modality is specified in the query."""

    def __init__(self, query_set: set[str], valid_order: list[str]) -> None:
        self.unsupported_modalities = query_set - set(valid_order)
        self.valid_order = valid_order
        msg = (
            f"Invalid query: [{', '.join(query_set)}]. "
            f"The provided modalities [{', '.join(self.unsupported_modalities)}] "
            f"are not supported. "
            f"Supported modalities are: {', '.join(valid_order)}"
        )
        super().__init__(msg)


class MissingDependencyModalityError(InterlacerQueryError):
    """Raised when modalities are missing their required dependencies."""

    def __init__(
        self, missing_dependencies: dict[str, set[str]], query_set: set[str]
    ) -> None:
        self.missing_dependencies = missing_dependencies
        self.query_set = query_set
        message = self._build_error_message()
        super().__init__(message)

    def _build_error_message(self) -> str:
        """Build a detailed error message showing all missing dependencies."""
        message = f"Invalid query: ({', '.join(self.query_set)})\n"
        message += (
            "The following modalities are missing required dependencies:\n"
        )

        for modality, required in self.missing_dependencies.items():
            message += (
                f"- {modality} requires one of: [{', '.join(required)}]\n"
            )

        return message


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
    folder : str
        Path to the folder containing the DICOM files
    ReferencedSeriesUID : str | None
        Series that this one references, if any
    children : list[SeriesNode]
        Child nodes representing referenced series
    """

    SeriesInstanceUID: str
    Modality: str
    PatientID: str
    StudyInstanceUID: str
    folder: str
    ReferencedSeriesUID: str | None = None
    children: list[SeriesNode] = field(default_factory=list, repr=False)

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
    root_nodes : list[SeriesNode]
        List of root nodes in the forest
    """

    crawl_index: str | Path | pd.DataFrame
    crawl_df: pd.DataFrame = field(init=False)
    series_nodes: dict[str, SeriesNode] = field(
        default_factory=dict, init=False
    )
    root_nodes: list[SeriesNode] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        """Initialize the Interlacer after dataclass initialization."""
        if isinstance(self.crawl_index, (str, Path)):
            self.crawl_df = pd.read_csv(self.crawl_index)
        elif isinstance(self.crawl_index, pd.DataFrame):
            self.crawl_df = self.crawl_index.copy()
        else:
            errmsg = f"Invalid type for crawl_index: {type(self.crawl_index)}"
            raise TypeError(errmsg)

        self.crawl_df.set_index("SeriesInstanceUID", inplace=True, drop=False)
        self.crawl_df = self.crawl_df[
            ~self.crawl_df.index.duplicated(keep="first")
        ]
        self._build_series_forest()

    def _build_series_forest(self) -> None:
        """
        Creates SeriesNode objects for each row in the DataFrame and
        constructs a forest of trees by defining parent-child relationships
        using ReferenceSeriesUID.
        """
        # Dictionary to track referenced UIDs that need to be connected later
        for index, row in self.crawl_df.iterrows():
            reference_series_uid = (
                row.ReferencedSeriesUID
                if "ReferencedSeriesUID" in row
                else None
            )

            # Create the SeriesNode
            self.series_nodes[str(index)] = SeriesNode(
                str(index),
                row.Modality,
                row.PatientID,
                row.StudyInstanceUID,
                row.folder,
                reference_series_uid,
            )

        for node in self.series_nodes.values():
            # Identify root nodes
            if node.Modality in ["CT", "MR"] or (
                node.Modality == "PT" and pd.isna(node.ReferencedSeriesUID)
            ):
                self.root_nodes.append(node)

            # Establish parent-child relationships if parent already exists
            if (
                pd.notna(node.ReferencedSeriesUID)
                and node.ReferencedSeriesUID in self.series_nodes
            ):
                parent_node = self.series_nodes[node.ReferencedSeriesUID]
                parent_node.add_child(node)

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

        Raises
        ------
        UnsupportedModalityError
            When the query contains modalities not in the valid_order list
        MissingDependencyModalityError
            When modalities in the query are missing their required dependencies
        """

        MODALITY_DEPENDENCIES: dict[str, set[str]] = {  # noqa: N806
            "RTSTRUCT": {"CT", "MR", "PT"},
            "RTDOSE": {"CT", "MR", "PT"},
            "SEG": {"CT", "MR"},
        }

        valid_order = ["CT", "MR", "PT", "SEG", "RTSTRUCT", "RTDOSE"]
        query_set = set(query)

        # Check for unsupported modalities
        if not query_set.issubset(set(valid_order)):
            raise UnsupportedModalityError(query_set, valid_order)

        # Collect all missing dependencies
        missing_dependencies = {}
        for modality in query:
            if modality in MODALITY_DEPENDENCIES:
                required = MODALITY_DEPENDENCIES[modality]
                if not query_set.intersection(required):
                    missing_dependencies[modality] = required

        # If any dependencies are missing, raise a comprehensive error
        if missing_dependencies:
            raise MissingDependencyModalityError(
                missing_dependencies, query_set
            )

        return [modality for modality in valid_order if modality in query_set]

    def _query(self, queried_modalities: list[str]) -> list[list[SeriesNode]]:
        """Find sequences containing queried modalities in order, optionally grouped by root."""
        results: list[list[SeriesNode]] = []

        # Special modalities that require direct connections to their dependencies
        SPECIAL_MODALITIES = {"SEG", "RTSTRUCT"}  # noqa: N806

        def dfs(node: SeriesNode, path: list[SeriesNode]) -> None:
            path.append(node)
            path_modalities = [n.Modality for n in path]

            if all(m in path_modalities for m in queried_modalities):
                # Check for special modality direct connection requirements
                valid_path = True
                for i, special_node in enumerate(path):
                    if (
                        special_node.Modality in SPECIAL_MODALITIES
                        and special_node.Modality in queried_modalities
                    ):
                        # The parent node must be in the query
                        parent = path[i - 1]
                        if parent.Modality not in queried_modalities:
                            valid_path = False
                            break

                if valid_path:
                    modality_nodes = [
                        n for n in path if n.Modality in queried_modalities
                    ]
                    if modality_nodes not in results:
                        results.append(modality_nodes)

            for child in node.children:
                dfs(child, path.copy())

        for root in self.root_nodes:
            dfs(root, [])

        return results

    def query_all(self) -> list[list[SeriesNode]]:
        """Simply return ALL possible matches
        Note this has a different approach than query, since we dont care
        about the order of the modalities, just that they exist in the
        Branch
        """
        results: list[list[SeriesNode]] = []

        def dfs(node: SeriesNode, path: list[SeriesNode]) -> None:
            path.append(node)
            if len(node.children) == 0:
                # If this is a leaf node, check if the path is unique
                # but first, if the path has any 'RTPLAN' nodes, remove them
                # TODO:: create a global VALID_MODALITIES list instead of hardcoding
                cleaned_path = [n for n in path if n.Modality != "RTPLAN"]
                if cleaned_path not in results:
                    results.append(cleaned_path)

            for child in node.children:
                dfs(child, path.copy())

        for root in self.root_nodes:
            dfs(root, [])
        return results

    def query(
        self,
        query_string: str,
        group_by_root: bool = True,
    ) -> list[list[SeriesNode]]:
        """
        Query the forest for specific modalities.

        Parameters
        ----------
        query_string : str
            Comma-separated string of modalities to query (e.g., 'CT,MR')

        group_by_root : bool, default=True
            If True, group the returned SeriesNodes by their root CT/MR/PT
            node (i.e., avoid duplicate root nodes across results).

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
        if query_string in ["*", "all"]:
            query_results = self.query_all()
        else:
            queried_modalities = self._get_valid_query(query_string.split(","))
            query_results = self._query(queried_modalities)

        if not group_by_root:
            return query_results

        grouped: dict[SeriesNode, set[SeriesNode]] = defaultdict(set)
        # pretty much start with the root node, then add all branches
        for path in query_results:
            root = path[0]
            grouped[root].update(path[1:])

        # break each item into a list starting with key, then all the values
        return [[key] + list(value) for key, value in grouped.items()]

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
    root_nodes: list[SeriesNode],
    input_directory: Path | None,
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
    from imgtools.dicom.crawl import Crawler

    dicom_dirs = [
        # Path("data/Vestibular-Schwannoma-SEG"),
        # Path("data/NSCLC_Radiogenomics"),
        # Path("data/Head-Neck-PET-CT"),
        # Path("data/4D-Lung"),
        # Path("data/Head-Neck-PET-CT/HN-CHUS-052/")
        Path("data/CPTAC-UCEC/C3L-00947"),
    ]
    interlacers = []
    for directory in dicom_dirs:
        crawler = Crawler(
            dicom_dir=directory,
            n_jobs=5,
            force=False,
        )
        crawler.crawl()

        interlacer = Interlacer(crawler.index)
        interlacers.append(interlacer)
        # interlacer.visualize_forest(
        #     directory.parent.parent / directory.name / "interlacer.html"
        # )
        # print(f"Query Result: {interlacer.query('MR,RTSTRUCT')}")

    for interlacer, input_dir in zip(interlacers, dicom_dirs):  # noqa
        interlacer.print_tree(input_dir)

        # query_results = interlacer.query("CT,RTSTRUCT", group_by_root=True)
        print(set(interlacer.query("CT,PT,RTSTRUCT")[0]))
