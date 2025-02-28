from pathlib import Path
from turtle import st
from typing import Dict, Iterator, List, Optional, Set

import pandas as pd
from pyvis.network import Network


# ruff: noqa
class SeriesNode:
    def __init__(self, row: pd.Series) -> None:
        self.Series: str = row.Index
        self.Modality: str
        self.PatientID: str
        self.folder: str
        self.ReferencedSeriesUID: Optional[str]
        for field in row._fields[1:]:  # Skip "Index" (first field)
            setattr(self, field, getattr(row, field))

        self.children: List["SeriesNode"] = []

    def add_child(self, child_node: "SeriesNode") -> None:
        """Add SeriesNode to children"""
        self.children.append(child_node)

    def __eq__(self, other: object) -> bool:
        """Equality check based on index"""
        if isinstance(other, str):  # Direct index check
            return self.Series == other
        return isinstance(other, SeriesNode) and self.Series == other.Series

    def __repr__(self, level: int = 0) -> str:
        """Recursive representation of the tree structure"""
        indent: str = "  " * level
        result: str = f"{indent}- {self.Modality}, (SERIES: {self.Series})\n"
        for child in self.children:
            result += child.__repr__(level + 1)
        return result


class Branch:
    def __init__(
        self, series_nodes: Optional[List[SeriesNode]] = None
    ) -> None:
        if series_nodes is None:
            series_nodes = []
        self.series_nodes: List[SeriesNode] = series_nodes

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
        return " -> ".join(node.Modality for node in self.series_nodes)


class Interlacer:
    def __init__(self, df: pd.DataFrame) -> None:
        self.forest: Dict[str, SeriesNode] = {}
        self.root_nodes: List[SeriesNode] = []
        self.df: pd.DataFrame = df
        self.branches: List[Branch] = []

        self._build_forest()
        self._find_branches()

    def _build_forest(self) -> None:
        """Constructs a forest of trees from the DataFrame by defining parent-child relationships."""
        # Step 1: Create nodes for all rows
        for row in self.df.itertuples():
            self.forest[row.Index] = SeriesNode(row)

        # Step 2: Establish parent-child relationships
        for row in self.df.itertuples():
            series_instance_uid: str = row.Index
            modality: str = row.Modality
            reference_series_uid: Optional[str] = row.ReferencedSeriesUID

            node: SeriesNode = self.forest[series_instance_uid]

            if modality in ["CT", "MR"] or (
                modality == "PT" and pd.isna(reference_series_uid)
            ):
                self.root_nodes.append(node)

            if (
                pd.notna(reference_series_uid)
                and reference_series_uid in self.forest
            ):
                parent_node: SeriesNode = self.forest[reference_series_uid]
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
        result: List[Branch] = []

        for branch in self.branches:
            present_modalities: Set[str] = {node.Modality for node in branch}
            if queried_modalities <= present_modalities:
                result.append(branch)

        return result

    def query(self, query_string: str) -> pd.DataFrame:
        """Queries the forest for specific modalities and returns a DataFrame."""
        queried_modalities: List[str] = query_string.split(",")
        query_result: List[Branch] = self._query(set(queried_modalities))

        data: List[Dict[str, str]] = [
            {
                "Patient_ID": branch.series_nodes[0].PatientID,
                **{
                    f"{field}_{modality}": getattr(
                        branch.get_modality_map().get(modality), field
                    )
                    for field in ["Series", "folder"]
                    for modality in queried_modalities
                },
            }
            for branch in query_result
        ]

        return pd.DataFrame.from_dict(data)

    def visualize_forest(self) -> None:
        """Visualizes the forest of SeriesNode objects as an interactive network graph."""
        net: Network = Network(
            height="800px", width="100%", notebook=False, directed=True
        )

        def add_node_and_edges(
            node: SeriesNode, parent: Optional[SeriesNode] = None
        ) -> None:
            net.add_node(node.Series, label=node.Modality, title=node.Series)
            if parent:
                net.add_edge(node.Series, parent.Series)
            for child in node.children:
                add_node_and_edges(child, node)

        for root in self.root_nodes:
            add_node_and_edges(root)

        net.force_atlas_2based()
        net.show_buttons(filter_=["physics"])

        save_path: Path = Path.cwd() / "forest_visualization.html"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        net.write_html(save_path.as_posix())


if __name__ == "__main__":
    df = pd.read_csv(
        ".imgtools/cache/final_meta.csv", index_col="SeriesInstanceUID"
    )
    import time

    start = time.time()
    interlacer = Interlacer(df)
    print(time.time() - start)

    start = time.time()
    print(interlacer.query("CT,RTSTRUCT").head())
    print(time.time() - start)
    print(interlacer.query("CT,PT,RTSTRUCT").head())
    print(interlacer.query("MR,RTSTRUCT").head())
