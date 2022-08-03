# Preparing Data for nnUNet

nnUNet repo can be found at: <https://github.com/MIC-DKFZ/nnUNet>

## Processing DICOM Data with Med-ImageTools

Ensure that you have followed the steps in <https://github.com/bhklab/med-imagetools#installing-med-imagetools> before proceeding.

To convert your data from DICOM to NIfTI for training an nnUNet auto-segmentation model, run the following command:

```sh
autopipeline\
  [INPUT DIRECTORY] \
  [OUTPUT DIRECTORY] \
  --modalities CT,RTSTRUCT \
  --nnunet
```

Modalities can also be set to `--modalities MR,RTSTRUCT`

## One-Step Preprocess and Train

Med-ImageTools generates a file in your output folder called `nnunet_preprocess_and_train.sh` that combines all the commands needed for preprocessing and training your nnUNet model. Run that shell script to get a fully trained nnUNet model with default settings.

Alternatively, you can go through each step individually as follows below:

## nnUNet Preprocessing

Follow the instructions for setting up your paths for nnUNet: <https://github.com/MIC-DKFZ/nnUNet/blob/master/documentation/setting_up_paths.md>

Med-ImageTools generates the dataset.json that nnUNet requires in the output directory that you specify.

The generated output directory structure will look something like:

```sh
OUTPUT_DIRECTORY
├── nnUNet_preprocessed
├── nnUNet_raw_data_base
│   └── nnUNet_raw_data
│       └── Task500_HNSCC
│           ├── nnunet_preprocess_and_train.sh
│           └── ...
└── nnUNet_trained_models
```

Too allow nnUNet to preprocess your data for trianing, run the following command. Set XXX to the ID that you want to preprocess. This is your task ID. For example, for Task500_HNSCC, the task ID is 500. Task IDs must be between 500 and 999, so Med-ImageTools can run 500 instances with the nnUNet flag in a single output folder.

```sh
nnUNet_plan_and_preprocess -t XXX --verify_dataset_integrity
```

Make sure that in your `~/.bashrc` file, the environment variable for nnUNet's nnUNet_raw_data_base environment variable looks like:

```sh
export nnUNet_raw_data_base="/OUTPUT_DIRECTORY/nnUNet_raw_data_base"
```

## nnUNet Training

Once nnUNet has finished preprocessing, you may begin training your nnUNet model. To train your model, run the following command. Learn more about nnUNet's options here: <https://github.com/MIC-DKFZ/nnUNet#model-training>

```sh
nnUNet_train CONFIGURATION TRAINER_CLASS_NAME TASK_NAME_OR_ID FOLD
```
