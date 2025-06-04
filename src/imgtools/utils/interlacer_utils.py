"""
Interlacer Utils Module

This module implements functions utilized by the Interlacer module as well as the SeriesNode dataclass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.theme import Theme
from rich.tree import Tree as RichTree

from imgtools.loggers import logger
from imgtools.utils import OptionalImportError, optional_import

pyvis, _pyvis_available = optional_import("pyvis")


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


def visualize_forest(
    root_nodes: list[SeriesNode], save_path: str | Path
) -> Path:
    """
    Visualize the forest as an interactive network graph.

    Creates an HTML visualization showing nodes for each SeriesNode and
    edges for parent-child relationships.

    Parameters
    ----------

    root_nodes: list[SeriesNode]
        the root nodes of the tree.

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
        title = (
            f"PatientID: {node.PatientID}\nSeries: {node.SeriesInstanceUID}"
        )
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
    for root in root_nodes:
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
