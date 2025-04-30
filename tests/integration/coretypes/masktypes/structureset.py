from imgtools.coretypes.masktypes import (
    ContourPointsAcrossSlicesError,
    MaskArrayOutOfBoundsError,
    NonIntegerZSliceIndexError,
    RTStructureSet,
    UnexpectedContourPointsError,
)
from pathlib import Path
import pytest
from rich import print

# TODO:: make these results as snapshots to compare with over time

def test_get_rtstructs(medimage_by_modality):
    """
    just test if we can initialize the RTStructureSet class for all
    the RTSTRUCTs in the test data
    
    """
    
    rtstructs = medimage_by_modality.get("RTSTRUCT")
    
    failures = {}
    successes = {}

    for rtstruct in rtstructs:
        try:
            rtstruct_obj = RTStructureSet.from_dicom(rtstruct['Path'])
            assert rtstruct_obj is not None
        except Exception as e:
            failures[rtstruct['Path']] = str(e)
        else:
            successes[rtstruct['Path']] = rtstruct_obj

    if failures:
        print("[red]Failed to initialize RTStructureSet for the following files:[/red]")
        for path, error in failures.items():
            print(f"[yellow]{path}[/yellow]: {error}")
        raise AssertionError("Some RTSTRUCT files failed to initialize.")

    rtstruct_errors = {}

    for path, rtstruct_obj in successes.items():
        if not rtstruct_obj.roi_map_errors:
            continue
        try:
            rtstruct_errors[path] = rtstruct_obj.roi_map_errors
        except Exception as e:
            rtstruct_errors[path] = str(e)

    # for debugging:
    # if rtstruct_errors:
    #     print("[red]Errors found in the following RTStructureSet objects:[/red]")
    #     for path, error_map in rtstruct_errors.items():
    #         # print(f"[yellow]{path}[/yellow]: {error}")
    #         for roi_name, error in error_map.items():
    #             relpath = path.relative_to(Path.cwd())
    #             print(f"[yellow]{relpath}[/yellow]: [green]{roi_name}[/green]: {error}")
    #     raise AssertionError("Some RTSTRUCT objects have errors.")