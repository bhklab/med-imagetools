This is a formalized definition of the roiname extraction to redesign the mess of how we used to handle it during the old `RTSTRUCT.to_segmentation`. 

`ROIMatchStrategy`
--------------
- these options are now mutually exclusive via an enum

```python
class ROIMatchStrategy(Enum):
    """Enum for ROI handling strategies."""
    MERGE =  "merge"       # merge all ROIs with the same key
    KEEP_FIRST =  "keep_first"  # keep the first matching ROI per key
    SEPARATE =  "separate"    # keep all matches as separate ROIs
```

`ROIMatcher`
----------

```python
PatternString = str
ROI_MatchingType = dict[str, list[PatternString]]
```

Implementation MUST define a dictionary mapping a key (general roi identifier i.e GTV)
to a list of [exact names OR regex patterns] 
if they ONLY provide a list WITHOUT a key, the default key is "ROI" (or whatever is passed)

Valid examples:
```python
roi_matcher = "GTV.*"                           # → {"ROI": ["GTV.*"]}
roi_matcher = ["GTVp", "CTV.*"]                 # → {"ROI": ["GTVp", "CTV.*"]}
roi_matcher = {"GTV": ["GTVp", "CTV.*"]}
roi_matcher = {"GTV": ["GTV.*"], "CTV": ["CTV.*"]}
```

Invalid examples:
```python
roi_matcher = 123                               # invalid (not str/list/dict)
roi_matcher = [["GTV.*", "CTV.*"]]              # invalid (nested list)
roi_matcher = {"GTV": {"GTVp": "GTVp.*"}}       # invalid (nested dict)
```

Matching Behavior
-----------------
Given a valid `ROI_Matching` input, combined with a `ROIMatchStrategy` strategy,
we choose to build a match_map using our roi names from the RTSTRUCT or SEG.

> [!NOTE]
> Matching is **case-insensitive** by default.

So given these rois (extracted names will be sorted alphabetically like this too)):
```python
roi_names = [
    'CTV_0', 'CTV_1', 'CTV_2',
    'ExtraROI', 'ExtraROI2',
    'GTV 0', 'GTVp',
    'PTV main', 'ptv x',
    '', 'UNKNOWN_ROI', 'gtv 0', 'extraROI'
]
```

and this roi_matching input:
```python
roi_matching = {
    "GTV": ["GTV.*"],
    "PTV": ["PTV.*"],
    "TV": ["GTV.*", "PTV.*", "CTV.*"],
    "extra": ["Extra.*"]
}
```

Here are the resulting extractions based on the handling strategy:
> [!NOTE]
> regardless of handling strategy, the matches will be stored in some
> metadata, so the user knows what was matched

## `ROIMatchStrategy.SEPARATE`

**case-sensitive**
```python
[
    "GTV__[GTV 0]", "GTV__[GTVp]",
    "PTV__[PTV main]",
    "TV__[GTV 0]", "TV__[GTVp]", "TV__[PTV main]", "TV__[CTV_0]", "TV__[CTV_1]", "TV__[CTV_2]",
    "extra__[ExtraROI]", "extra__[ExtraROI2]"
]
```

**case-insensitive**
```python
[
    "GTV__[GTV 0]", "GTV__[GTVp]", "GTV__[gtv 0]",
    "PTV__[PTV main]", "PTV__[ptv x]",
    "TV__[GTV 0]", "TV__[GTVp]", "TV__[gtv 0]", "TV__[PTV main]", "TV__[ptv x]", "TV__[CTV_0]", "TV__[CTV_1]", "TV__[CTV_2]",
    "extra__[ExtraROI]", "extra__[ExtraROI2]", "extra__[extraROI]"
]
```

`ROIMatchStrategy.MERGE`
> [!NOTE]
> merging still means a binary mask, no argmax nonsense here
**case-sensitive**

```python
[
    "GTV",     # from: ["GTV 0", "GTVp"]
    "PTV",     # from: ["PTV main"]
    "TV",      # from: ["GTV 0", "GTVp", "PTV main", "CTV_0", "CTV_1", "CTV_2"]
    "extra"    # from: ["ExtraROI", "ExtraROI2"]
]
```
**case-insensitive**
```python
[
    "GTV",     # from: ["GTV 0", "GTVp", "gtv 0"]
    "PTV",     # from: ["PTV main", "ptv x"]
    "TV",      # from: ["GTV 0", "GTVp", "gtv 0", "PTV main", "ptv x", "CTV_0", "CTV_1", "CTV_2"]
    "extra"    # from: ["ExtraROI", "ExtraROI2", "extraROI"]
]
```

> [!WARNING]
> `ROIMatchStrategy.KEEP_FIRST` is strongly discouraged, as the first roi found is never guaranteed to be the most relevant one.
> Nonetheless, exact ROI pattern names are preferred to generalized regex matching
> i.e ("CTV_0" is preferred to "CTV.*") to ensure some level of confidence in the matching.

`ROIMatchStrategy.KEEP_FIRST`
**case-sensitive**
```python
[
    "[GTV]__GTV_0",  # `GTV 0` comes first before `GTVp`
    "[PTV]__PTV",   # `PTV` comes first before `ptv x`

    # `CTV_0` comes first before all other matches in the sorted list 
    # BUT we specifically had 'GTV.*' first in the list
    "[TV]__GTV_0",  

    # `ExtraROI` got matched because it was an exact pattern
    "[extra]__ExtraROI",
]
```

**case-insensitive**
same as above!
```python
[
    "[GTV]__GTV_0",  # `GTV 0` comes first before `GTVp`
    "[PTV]__PTV",   # `PTV` comes first before `ptv x`

    # `CTV_0` comes first before all other matches in the sorted list 
    # BUT we specifically had 'GTV.*' first in the list
    "[TV]__GTV_0",  

    # `ExtraROI` got matched because it was an exact pattern
    "[extra]__ExtraROI",
]
```