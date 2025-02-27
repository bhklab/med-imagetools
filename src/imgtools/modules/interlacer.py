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
        self.branches: List[Branch] = []

        self._build_forest()
        self._find_branches()

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

    def _find_branches(self) -> None:
        """Finds and records all branches in the forest using depth-first search (DFS)."""
        def traverse_tree(node: SeriesNode, branch: List[SeriesNode]) -> None:
            branch.append(node)
            if node.children:
                for child in node.children:
                    traverse_tree(child, branch.copy())
            else:
                self.branches.append(Branch(branch))

        for root in self.root_nodes:
            traverse_tree(root, [])

    def _query(self, queried_modalities: Set[str]) -> List[Branch]:
        """Returns Branches that contain *all* specified modalities."""
        result = []

        for branch in self.branches:
            present_modalities = {node.Modality for node in branch} 
            if queried_modalities <= present_modalities:
                result.append(branch)

        return result

    def query(self, query_string: str) -> pd.DataFrame:
        """
        Queries the forest for specific modalities and returns a DataFrame containing relevant patient data.

        Parameters
        ----------
        query_string : str
            A comma-separated string representing the modalities to query (e.g., 'CT,MR').

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
        query_result = self._query(set(queried_modalities))

        data = [
            {
                'PatientID': branch.series_nodes[0].PatientID,  # Patient ID (same for all nodes)
                **{
                    f'{field}_{modality}': getattr(branch.get_modality_map().get(modality), field)
                    for field in ['Series', 'folder']
                    for modality in queried_modalities 
                }
            }
            for branch in query_result
        ]
        
        return pd.DataFrame(data)
    
    def visualize_forest(self, save_path: str | Path) -> None:
        """
        Visualizes the forest of `SeriesNode` objects as an interactive network graph.

        The visualization is saved as an HTML file (`forest_visualization.html`), displaying nodes 
        for each `SeriesNode` and edges representing parent-child relationships.
        """
        if not _pyvis_available:
            raise OptionalImportError("pyvis")

        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        net = pyvis.network.Network(height='800px', width='100%', notebook=False, directed=True)

        def add_node_and_edges(node: SeriesNode, parent: SeriesNode | None = None) -> None:
            net.add_node(node.Series, label=node.Modality, title=node.Series)  # Display Series on click
            if parent:
                net.add_edge(node.Series, parent.Series) 
            for child in node.children:
                add_node_and_edges(child, node) 

        for root in self.root_nodes:
            add_node_and_edges(root)

        net.force_atlas_2based()
        net.show_buttons(filter_=['physics'])

        logger.info("Saving forest visualization...", path=save_path)
        net.write_html(save_path.as_posix())

