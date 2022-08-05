# AutoPipeline Usage

To use AutoPipeline, follow the installation instructions found at <https://github.com/bhklab/med-imagetools#installing-med-imagetools>.

AutoPipeline will crawl and process any DICOM dataset. To run the most basic variation of the script, run the following command:

```sh
autopipeline INPUT_DIRECTORY OUTPUT_DIRECTORY --modalities MODALITY_LIST
```

Replace INPUT_DIRECTORY with the directory containing all your DICOM data, OUTPUT_DIRECTORY with the directory that you want the data to be outputted to.

The `--modalities` option allows you to only process certain modalities that are present in the DICOM data. The available modalities are:

1. CT
2. MR
3. RTSTRUCT
4. PT
5. RTDOSE

Set the modalities you want to use by separating each one with a comma. For example, to use CT and RTSTRUCT, run AutoPipeline with `--modalities CT,RTSTRUCT`

AutoPipeline comes with many more built-in features to make your data conversion easier:

1. **YAML for Label Regexes**

    Whether to read a YAML file that defines regexes for label names for regions of interest. By default, it will look for and read from `INPUT_DIRECTORY/roi_names.yaml`

    ```sh
    --read_yaml_label_names [flag]
    ```

    Path to the above-mentioned YAML file. Path can be absolute or relative. default = "" (each ROI will have its own label index in dataset.json for nnUNet)

    ```sh
    --roi_yaml_path [str]
    ```

    <details open>
    <summary>Click for example</summary>
    For example, if the YAML file contains:

    ```yaml
    GTV: GTV*
    ```

    All ROIs that match the regex of GTV* (e.g. GTVn, GTVp, GTVfoo) will be saved to one label under the name of GTV
    </details>

    Ignore patients with no labels that match any regexes instead of throwing error.

    ```sh
    --ignore_missing_regex [flag]
    ```

2. **Spacing**

    The spacing for the output image. default = (1., 1., 0.)

    ```sh
    --spacing [Tuple: (int,int,int)]
    ```

3. **Parallel Job Execution**

    The number of jobs to be run in parallel. Set -1 to use all cores. default = -1

    ```sh
    --n_jobs [int]
    ```

4. **Dataset Graph Visualization (not recommended for large datasets)**

    Whether to visualize the entire dataset using PyViz.

    ```sh
    --visualize [flag]
    ```

5. **Continue Pipeline Processing**

    Whether to continue the most recent run of AutoPipeline that terminated prematurely for that output directory. Will only work if the `.imgtools` directory was not deleted from previous run. Using this flag will retain the same flags and parameters carried over from the previous run.

    ```sh
    --continue_processing [flag]
    ```

6. **Dry Run for Indexed Dataset**

    Whether to execute a dry run, only generating the .imgtools folder.

    ```sh
    --dry_run [flag]
    ```

7. **Show Progress**

    Whether to print processing progress to the standard output.

    ```sh
    --show_progress [flag]
    ```

8. **Warning on Subject Processing Errors**

    Whether to warn instead of error when processing subjects

    ```sh
    --warn_on_error [flag]
    ```

9. **Overwrite Existing Output Files**

    Whether to overwrite exisiting file outputs

    ```sh
    --overwrite [flag]
    ```

For nnUNet:

1. **Format Output for nnUNet Training**

    Whether to format output for nnUNet training. Modalities must be CT,RTSTRUCT or MR,RTSTRUCT. `--modalities CT,RTSTRUCT` or `--modalities MR,RTSTRUCT`

    ```sh
    --nnunet [flag]
    ```

    ```sh
    OUTPUT_DIRECTORY
    ├── nnUNet_preprocessed
    ├── nnUNet_raw_data_base
    │   └── nnUNet_raw_data
    │       └── Task500_HNSCC
    │           ├── imagesTr
    │           ├── imagesTs
    │           ├── labelsTr
    │           └── labelsTs
    └── nnUNet_trained_models
    ```

2. **Training Size**

    Training size of the train-test-split. default = 1.0 (all data will be in imagesTr/labelsTr)

    ```sh
    --train_size [float]
    ```

3. **Random State**

    Random state for the train-test-split. Uses sklearn's train_test_split(). default = 42

    ```sh
    --random_state [int]
    ```

4. **Custom Train-Test-Split YAML**

    Whether to use a custom train-test-split. Must be in a file found at `INPUT_DIRECTORY/custom_train_test_split.yaml`. All subjects not defined in this file will be randomly split to fill the defined value for `--train_size` (default = 1.0). File must conform to:

    ```yaml
    train:
        - subject_1
        - subject_2
        ...
    test:
        - subject_1
        - subject_2
        ...
    ```

    ```sh
    --custom_train_test_split [flag]
    ```

For nnUNet Inference:

1. **Format Output for nnUNet Inference**

    Whether to format output for nnUNet Inference.

    ```sh
    --nnunet_inference [flag]
    ```

    ```sh
    OUTPUT_DIRECTORY
    ├── 0_subject1_0000.nii.gz
    └── ...
    ```

2. **Path to `dataset.json`**

    The path to the `dataset.json` file for nnUNet inference.

    ```sh
    --dataset_json_path [str]
    ```
