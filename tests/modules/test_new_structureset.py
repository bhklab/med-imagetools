from pathlib import Path
from typing import Dict, List

import numpy as np
import pytest
from rich import print  # noqa
from rich.console import Console
from rich.pretty import Pretty
from rich.table import Table
from sqlalchemy import true

from imgtools.modules.structureset.rt_structureset import (  # type: ignore
    ROI,
    ContourSlice,
    ROINamePatterns,
    RTSTRUCTMetadata,
    RTStructureSet,
)


@pytest.fixture
def rt_metadata() -> RTSTRUCTMetadata:
    return RTSTRUCTMetadata(
        PatientID="123456",
        Modality="RTSTRUCT",
        StudyInstanceUID="123456",
        SeriesInstanceUID="123456",
        ReferencedStudyInstanceUID="123456",
        ReferencedSeriesInstanceUID="123456",
        OriginalROIMeta=[],
        OriginalNumberOfROIs=0,
    )


@pytest.fixture
def roi_points() -> Dict[str, List[np.ndarray]]:
    """Fixture for mock ROI points."""
    return {
        "GTV_oopsies": [np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])],
        "GTV": [np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])],
        "PTV": [np.array([[2.0, 2.0, 2.0], [3.0, 3.0, 3.0]])],
        "CTV": [np.array([[4.0, 4.0, 4.0], [5.0, 5.0, 5.0]])],
        "CTV_another": [np.array([[6.0, 6.0, 6.0], [7.0, 7.0, 7.0]])],
        "CTV_another2": [np.array([[8.0, 8.0, 8.0], [9.0, 9.0, 9.0]])],
        "ExtraROI": [np.array([[10.0, 10.0, 10.0], [11.0, 11.0, 11.0]])],
        "ExtraROI2": [np.array([[12.0, 12.0, 12.0], [13.0, 13.0, 13.0]])],
    }


@pytest.fixture
def rtss(
    roi_points: Dict[str, List[np.ndarray]], rt_metadata: RTSTRUCTMetadata
) -> RTStructureSet:
    """Fixture for RTStructureSet instance."""
    roi_names = list(roi_points.keys())
    contours = {}
    for name, points in roi_points.items():
        c_slices = [ContourSlice(pointarr) for pointarr in points]
        contours[name] = c_slices

    roi_dict = {
        name: ROI(
            name=name, ReferencedROINumber=i, num_points=1, slices=c_slices
        )
        for i, (name, c_slices) in enumerate(contours.items())
    }
    return RTStructureSet(
        roi_names=roi_names, roi_map=roi_dict, metadata=rt_metadata
    )


def test_run_rtss_tests_and_display(rtss: RTStructureSet) -> None:
    """Run tests for _handle_roi_names and display results in a Rich table."""
    results_dict = []

    # Define test cases
    test_cases: list[ROINamePatterns] = [
        # Empty list case
        [],
        None,
        "GTV.*",
        ".*TV.*",
        "^GTV$",  # Exact match
        "GTV",  # Another exact match
        # Simple list-based patterns
        ["GTV", "PTV"],
        ["GTV.*", "P.*"],
        ["CTV.*"],
        [["GTV.*", "PTV.*"], "CTV.*"],
        # Dictionary-based mappings
        {},  # Empty dictionary case
        {"GTV": ["GTV"], "Plan": ["PTV"]},
        {"GTV": "CTV.*", "Plan": ["PTV", "GTV"]},
        {"Primary": [["GTV", "PTV"], "CTV.*"], "GTV": "GTV.*"},  # GTV twice
        {"Primary": [["GTV", "PTV"], "CTV.*"], "Extra": "Extra.*"},
    ]

    # Run tests and collect results
    for names in test_cases:
        result = rtss._handle_roi_names(names)
        result_entry = {
            "Input": names,
            "Output": result,
        }
        results_dict.append(result_entry)

    all_roi_names = rtss.roi_names

    print(f"\n[bold green]All ROI names:[/bold green] {all_roi_names}")

    # Create a single table for all types of keys with sections
    table = Table(title="ROI Name Matching Results", expand=True)
    table.add_column("Input", justify="left", style="cyan", no_wrap=False)
    table.add_column("Output", justify="left", style="green", no_wrap=False)

    # Add section headers
    table.add_section()
    for result_e in results_dict:
        key = result_e["Input"]
        value = result_e["Output"]
        if isinstance(key, (str, type(None))):
            table.add_row(str(key), str(value))

    table.add_section()
    for result_e in results_dict:
        key = result_e["Input"]
        value = result_e["Output"]
        if isinstance(key, list):
            table.add_row(str(key), str(value))

    table.add_section()
    # Add section headers
    table.add_row("Dictionary-based patterns", "Results")
    table.add_section()
    for result_e in results_dict:
        key = result_e["Input"]
        value = result_e["Output"]
        if isinstance(key, dict):
            table.add_row(
                Pretty(key, expand_all=True), Pretty(value, expand_all=True)
            )
            table.add_section()

    # Print the results using Rich
    console = Console()
    console.print(table)


# Run everything
if __name__ == "__main__":
    pytest.main([__file__, "-s"])
