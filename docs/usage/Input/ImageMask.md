# Loading Images and Masks from DICOMs


```python
from imgtools.ops.input_classes import ImageMaskInput, ImageMaskModalities
from imgtools.logging import logger
from pathlib import Path

logger.setLevel("ERROR")
```

## Getting Started

You need the following at minimum:
- Path to the directory containing the DICOM files
- Establish which Image and Mask modalities you want to use:
Combinations are:  

| Image Modality | Mask Modality |
|----------------|---------------|
| CT             | RTSTRUCT      |
| MR             | RTSTRUCT      |
| CT             | SEG      |
| MR             | SEG      |

For this tutorial we will download two datasets:



```python
# Define the path to the data
testdata = Path("testdata")
# for this tutorial we will use some test image data
datasets_name = ["NSCLC-Radiomics", "Vestibular-Schwannoma-SEG"]
```


```python
%%capture 
# download data using the imgtools cli
!imgtools testdata -a Vestibular-Schwannoma-SEG.tar.gz -a NSCLC-Radiomics.tar.gz {testdata.absolute()}
```

## Setting up the loaders with `ImageMaskInput`

### Vestibular-Schwannoma-SEG

has MR as scan and RTSTRUCT as mask:


| Patient ID           | Modality  | Number of Series    |
|----------------------|-----------|---------------------|
| VS-SEG-001           | MR        | 2                   |
| VS-SEG-001           | RTSTRUCT  | 2                   |
| VS-SEG-002           | MR        | 2                   |
| VS-SEG-002           | RTSTRUCT  | 2                   |


```python
vs_seg = ImageMaskInput(
  dir_path=testdata / datasets_name[1],
  modalities=ImageMaskModalities.MR_RTSTRUCT
)

print(vs_seg)
```

    ImageMaskInput<
    	num_cases=4,
    	dataset_name='Vestibular-Schwannoma-SEG',
    	modalities=<MR,RTSTRUCT>,
    	output_streams=['MR', 'RTSTRUCT_MR'],
    	series_col_names=['series_MR', 'series_RTSTRUCT_MR'],
    >


### NSCLC-Radiomics

has CT as scan and BOTH RTSTRUCT and SEG as masks.

| Patient ID           | Modality  | Number of Series    |
|----------------------|-----------|---------------------|
| LUNG1-001            | CT        | 1                   |
| LUNG1-001            | RTSTRUCT  | 1                   |
| LUNG1-001            | SEG       | 1                   |
| LUNG1-002            | CT        | 1                   |
| LUNG1-002            | RTSTRUCT  | 1                   |
| LUNG1-002            | SEG       | 1                   |


```python
nsclsc_rtstruct = ImageMaskInput(
    dir_path=testdata / datasets_name[0],
    modalities=ImageMaskModalities.CT_RTSTRUCT
)
print(nsclsc_rtstruct)
```

    ImageMaskInput<
    	num_cases=2,
    	dataset_name='NSCLC-Radiomics',
    	modalities=<CT,RTSTRUCT>,
    	output_streams=['CT', 'RTSTRUCT_CT'],
    	series_col_names=['series_CT', 'series_RTSTRUCT_CT'],
    >



```python
nsclsc_seg = ImageMaskInput(
    dir_path=testdata / datasets_name[0],
    modalities=ImageMaskModalities.CT_SEG
)
print(nsclsc_seg)
```

    ImageMaskInput<
    	num_cases=2,
    	dataset_name='NSCLC-Radiomics',
    	modalities=<CT,SEG>,
    	output_streams=['CT', 'SEG'],
    	series_col_names=['series_CT', 'series_SEG'],
    >


## Using the Input Datasets


```python
# List the case IDs (subject IDs)
print(nsclsc_rtstruct.keys())
```

    ['0_LUNG1-002', '1_LUNG1-001']


### Load a case


```python
# by case ID or index
caseid = '0_LUNG1-002'
case = nsclsc_rtstruct[caseid]
# get the image and mask 
image = case.CT 
structureset = case.RTSTRUCT
```


```python
#view
image
```




    Scan<
    	BodyPartExamined=LUNG
    	SliceThickness=3.00000
    	PatientPosition=HFS
    	Manufacturer=CMS, Inc.
    	RescaleSlope=1
    	ManufacturerModelName=XiO
    	PixelSize=('0.9770', '0.9770', '3.00000')
    	KVP=None, size=(512, 512, 111)
    	spacing=(0.977, 0.977, 3.0)
    	origin=(-250.112, -250.112, -133.4)
    	direction=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
    >



### StructureSets need to be converted to `Segmentation` objects


```python
#view
print(structureset)
mask = structureset.to_segmentation(image, "GTV-1")
mask
```

    
    <StructureSet
    	ROIs: ['Esophagus', 'GTV-1', 'Heart', 'Lung-Left', 'Lung-Right', 'Spinal-Cord']
    	Metadata:
    		PatientID: LUNG1-002
    		StudyInstanceUID: 85095 (truncated)
    		SeriesInstanceUID: 45931 (truncated)
    		Modality: RTSTRUCT
    		ReferencedSeriesInstanceUID: 61228 (truncated)
    		OriginalNumberOfROIs: 6
    		ExtractedNumberOfROIs: 6
    		Manufacturer: Varian Medical Systems
    		ManufacturerModelName: ARIA RadOnc
    		numROIs: 6
    >





    <Segmentation with ROIs: {'GTV-1': 1}>



### Whereas native `SEG` modalities get loaded as `Segmentation` objects


```python
# by case ID or index
caseid = nsclsc_seg.keys()[0]
case_seg = nsclsc_seg[caseid]
image = case_seg.CT
mask = case_seg.SEG
mask
```




    <Segmentation with ROIs: {'label_1': 1}>



### MR & RTSTRUCT example


```python
case_id = vs_seg.keys()[0]
case = vs_seg[case_id]
image = case.MR
structureset = case.RTSTRUCT
print(structureset.roi_names)
```

    ['*Skull', 'TV', 'cochlea']



```python
mask = structureset.to_segmentation(image, "TV")
mask
```




    <Segmentation with ROIs: {'TV': 1}>


