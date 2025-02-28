from __future__ import annotations
from typing import Dict, Iterator, List, Set
from pathlib import Path

import pandas as pd

from imgtools.logging import logger
from imgtools.utils import optional_import, OptionalImportError

pyvis, _pyvis_available = optional_import("pyvis")

class SeriesNode():
    def __init__(self, series: str, row: pd.Series) -> None:
        self.Series = series
        self.Modality = row.Modality
        self.PatientID = row.PatientID
        self.folder = row.folder

        self.children: List[SeriesNode] = []  

    def add_child(self, child_node: SeriesNode) -> None:
        """Add SeriesNode to children"""
        self.children.append(child_node)
    
    def get_all_nodes(self) -> List[SeriesNode]:
        """Recursively return all nodes in the tree, including root node and all descendants"""
        all_nodes = [self]  # Start with the current node
        for child in self.children:
            all_nodes.extend(child.get_all_nodes())  # Recursively add all nodes from children
        return all_nodes

    def __eq__(self, other: object) -> bool:
        """Equality check based on index"""
        if isinstance(other, str):  # Direct index check
            return self.Series == other
        return isinstance(other, SeriesNode) and self.Series == other.Series

    def __repr__(self, level:int = 0) -> str:
        """Recursive representation of the tree structure"""
        indent = "  " * level
        result = f"{indent}- {self.Modality}, (SERIES: {self.Series})\n"
        for child in self.children:
            result += child.__repr__(level + 1)
        return result
    
class Branch:
    def __init__(self, series_nodes: List[SeriesNode] | None = None) -> None:
        self.series_nodes = [] if series_nodes is None else series_nodes

    def add_node(self, node: SeriesNode) -> None:
        """Add a SeriesNode to the branch."""
        self.series_nodes.append(node)
    
    def get_modality_map(self) -> Dict[str, SeriesNode]:
        """Returns a dictionary mapping Modality to SeriesNode."""
        return {node.Modality: node for node in self.series_nodes}

    def __iter__(self) -> Iterator[SeriesNode]:
        """Yield the node from each SeriesNode in the branch."""
        for node in self.series_nodes:
            yield node

    def __repr__(self) -> str:
        """Return a string representation of the branch."""
        return ' -> '.join(node.Modality for node in self.series_nodes)

class Interlacer:
    def __init__(self, crawl_path: str | Path) -> None:
        self.df = pd.read_csv(crawl_path, index_col='SeriesInstanceUID')

        self.forest: Dict[str, SeriesNode] = {} 
        self.root_nodes: List[SeriesNode] = [] 

        self._build_forest()

    def _build_forest(self) -> None:
        """Constructs a forest of trees from the DataFrame by defining parent-child relationships."""
        # Step 1: Create nodes for all rows
        for index, row in self.df.iterrows():
            series_instance_uid = str(index)
            self.forest[series_instance_uid] = SeriesNode(series_instance_uid, row.astype(str))

        # Step 2: Establish parent-child relationships
        for index, row in self.df.iterrows():
            series_instance_uid = str(index)
            modality = row.Modality
            reference_series_uid = row.ReferencedSeriesUID

            node = self.forest[series_instance_uid]

            if modality in ["CT", "MR"] or (modality == "PT" and pd.isna(reference_series_uid)):
                self.root_nodes.append(node)

            if pd.notna(reference_series_uid) and reference_series_uid in self.forest:
                parent_node = self.forest[reference_series_uid]
                parent_node.add_child(node)

    def _find_branches(self) -> List[Branch]:
        """Finds and records all branches in the forest using depth-first search (DFS)."""
        branches: List[Branch] = []
        def traverse_tree(node: SeriesNode, branch: List[SeriesNode]) -> None:
            branch.append(node)
            if node.children:
                for child in node.children:
                    traverse_tree(child, branch.copy())
            else:
                branches.append(Branch(branch))

        for root in self.root_nodes:
            traverse_tree(root, [])
        
        return(branches)

    def _query(self, queried_modalities: Set[str], process_branches: bool = True) -> List[Branch]:
        """Returns samples that contain *all* specified modalities."""
        result = []

        if process_branches: # Make branches from tree then query  
            branches = self._find_branches()
            for branch in branches:
                series_nodes = [node for node in branch if node.Modality in queried_modalities]
                present_modalities = {node.Modality for node in series_nodes} 
                if queried_modalities <= present_modalities:
                    result.append(series_nodes)
        else: # Query on full tree
            for root in self.root_nodes: 
                series_nodes = [node for node in root.get_all_nodes() if node.Modality in queried_modalities]
                present_modalities = {node.Modality for node in series_nodes} 
                if queried_modalities == present_modalities:
                    result.append(series_nodes)

        return result

    def query(self, query_string: str, process_branches: bool = False) -> pd.DataFrame:
        """
        Queries the forest for specific modalities and returns a DataFrame containing relevant patient data.

        Parameters
        ----------
        query_string : str
            A comma-separated string representing the modalities to query (e.g., 'CT,MR').
        process_branches : bool, optional, default=False
            If True, queries all branches as different samples
        Returns
        -------
        pd.DataFrame
            A DataFrame where each row contains the `Patient_ID`, and for each modality, the corresponding `Series` and `Folder`.

        Supported Modalities
        --------------------
        The following modalities are supported for querying:
        - 'CT'        : Computed Tomography
        - 'PT'        : Positron Emission Tomography
        - 'MR'        : Magnetic Resonance Imaging
        - 'SEG'       : Segmentation
        - 'RTSTRUCT'  : Radiotherapy Structure
        - 'RTDOSE'    : Radiotherapy Dose
        """
        queried_modalities = query_string.split(',')
        query_results = self._query(set(queried_modalities), process_branches)

        data = [
            [
                {
                    'Series': node.Series,
                    'Modality': node.Modality
                }
                for node in result
            ]
            for result in query_results
        ]

        return data
    
    def visualize_forest(self, save_path: str | Path | None = None) -> None:
        """
        Visualizes the forest of `SeriesNode` objects as an interactive network graph.

        The visualization is saved as an HTML file (`forest_visualization.html`), displaying nodes 
        for each `SeriesNode` and edges representing parent-child relationships.
        """
        if not _pyvis_available:
            raise OptionalImportError("pyvis")

        save_path = './forest_visualization.html' if save_path is None else save_path
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        net = pyvis.network.Network(height='800px', width='100%', notebook=False, directed=True)

        modality_colors = {
            "CT": "#1f77b4",    # Blue
            "MR": "#ff7f0e",   # Orange
            "PT": "#2ca02c",   # Green
            "SEG": "#d62728", # Red
            "RTSTRUCT": "#9467bd", # Purple
            "RTPLAN": "#8c564b", # Brown
            "RTDOSE": "#e377c2" # Pink
        }

        patient_trees = {}  # Store patient-to-root mappings

        def add_node_and_edges(node: SeriesNode, parent: SeriesNode | None = None) -> None:
            color = modality_colors.get(node.Modality, "#7f7f7f")  # Default gray if unknown
            title = f'PatientID: {node.PatientID}\nSeries: {node.Series}'
            net.add_node(node.Series, label=node.Modality, title=title, color=color)
            if parent:
                net.add_edge(node.Series, parent.Series)

            for child in node.children:
                add_node_and_edges(child, node)

        # Add root nodes (each representing a patient)
        for root in self.root_nodes:
            add_node_and_edges(root)
            patient_trees[root.PatientID] = root.Series  # Store the root Series as entry point for the patient

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
                network.focus(nodeId, { scale: 1.5, animation: true });
            }
        </script>
        """

        # Generate the full HTML file
        logger.info("Saving forest visualization...", path=save_path)
        net_html = net.generate_html()
        full_html = net_html.replace("<body>", f"<body>{sidebar_html}")  # Insert sidebar into HTML

        # Write the final HTML file
        save_path.write_text(full_html, encoding="utf-8")

