# IO module

## Input
* ImageAutoInput
* ImageCSVInput
* ImageFileInput

### 1. Initialize loader with required parameters
* ImageCSVInput
    * `csv_path_or_dataframe` (str): Path to CSV or pandas DataFrame instance
    * `colnames` (List[str]): Columns that store path to images. Passed to `pd.read_csv(usecols=colnames)`
    * `id_column` (int): Index of index column. Passed to `pd.read_csv(index_col=id_column)`
    * `expand_paths` (bool): Expand paths deeper.
    * `readers` (List[Callable]): List of function used to read individual images. 
* ImageFileInput
    * `root_directory` (str): Parent directory of all subject directories
    * `get_subject_id_from` (str): Specify how to derive subject_id of a sample. ['filename', 'subject_directory']
    * `subdir_path` (str): If images are stored in a subdirectory of the subject diretory. Accepts glob expressions for flexible subdirectory names.
    * `reader` (List[Callable]): Function used to read individual images
* ImageAutoInput
    * `dir_path` (str): Path to dataset top-level directory.
    * `modality` (str): List of modalities to process. Only samples with ALL modalities will be processed. Make sure there are no space between list elements as it is parsed as a string.
    * `n_jobs` (Optional(int)): Number of threads to use for multiprocessing.


### 2. Call loader with subject_id

### Code Examples
```
input = ImageCSVInput("folder/to/dataset/indexing.csv",
                      colnames=['ct_path', 'rt_path'],
                      index_col=0
                      readers=['read_dicom_series', 'read_dicom_rtstruct'])


image, structureset = input(subject_id)
```

```
input = ImageFileInput("folder/to/dataset/images",
                       get_subject_id_from='subject_directory',
                       subdir_path="*/structures/RTSTRUCT.dcm",
                       reader='read_dicom_rtstruct')

image = input(subject_id)
```
    
```
input = ImageAutoInput("folder/to/dataset",
                       modality="CT,RTSTRUCT")

image, structureset = input(subject_id)
```
    