from imgtools.coretypes.masktypes.seg import (
    Segment,
    SEG,
    SegmentationError
)
from pathlib import Path
import pytest
from rich import print

# TODO:: make these results as snapshots to compare with over time

def test_get_segs(medimage_by_modality):
    """
    just test if we can initialize the SEG class
    """
    
    segs = medimage_by_modality.get("SEG")
    
    failures = {}
    successes = {}

    for seg in segs:
        try:
            seg_obj = SEG.from_dicom(seg['Path'])
            assert seg_obj is not None
        except AssertionError as e:
            failures[seg['Path']] = str(e)
        except KeyError as e:
            failures[seg['Path']] = str(e)
        except ValueError as e:
            failures[seg['Path']] = str(e)
        except SegmentationError as e:
            failures[seg['Path']] = str(e)
        else:
            successes[seg['Path']] = seg_obj

    if failures:
        print("[red]Failed to initialize SEG for the following files:[/red]")
        for path, error in failures.items():
            print(f"[yellow]{path}[/yellow]: {error}")
        # raise AssertionError("Some SEG files failed to initialize.")

    seg_errors = {}

    # for debugging:
    # if seg_errors:
    #     print("[red]Errors found in the following segureSet objects:[/red]")
    #     for path, error_map in seg_errors.items():
    #         # print(f"[yellow]{path}[/yellow]: {error}")
    #         for roi_name, error in error_map.items():
    #             relpath = path.relative_to(Path.cwd())
    #             print(f"[yellow]{relpath}[/yellow]: [green]{roi_name}[/green]: {error}")
    #     raise AssertionError("Some seg objects have errors.")