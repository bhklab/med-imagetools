from typing import Tuple, List
import os
import pathlib
import glob
import json
import numpy as np
import matplotlib.pyplot as plt


def markdown_report_images(output_folder, modality_count):
    modalities = list(modality_count.keys())
    modality_totals = list(modality_count.values())
    if not os.path.exists(pathlib.Path(output_folder, "markdown_images").as_posix()):
        os.makedirs(pathlib.Path(output_folder, "markdown_images").as_posix())
    plt.figure(1)
    plt.bar(modalities, modality_totals)
    plt.savefig(pathlib.Path(output_folder, "markdown_images", "nnunet_modality_count.png").as_posix())

    plt.figure(2)
    train_total = len(glob.glob(pathlib.Path(output_folder, "labelsTr", "*.nii.gz").as_posix()))
    test_total = len(glob.glob(pathlib.Path(output_folder, "labelsTs", "*.nii.gz").as_posix()))
    plt.pie([train_total, test_total], labels=[f"Train - {train_total}", f"Test - {test_total}"])
    plt.savefig(pathlib.Path(output_folder, "markdown_images", "nnunet_train_test_pie.png").as_posix())


def save_json(obj, file: str, indent: int = 4, sort_keys: bool = True) -> None:
    with open(file, 'w') as f:
        json.dump(obj, f, sort_keys=sort_keys, indent=indent)

def create_train_script(output_directory, dataset_id):
    """
    Creates a bash script (`train.sh`) for running nnUNet training, with paths for raw data,
    preprocessed data, and trained models. The script ensures environment variables are set and 
    executes the necessary training commands.

    Parameters:
    - output_directory (str): The directory where the output and subdirectories are located.
    - dataset_id (int): The ID of the dataset to be processed.
    """
    # Define paths using pathlib
    output_directory = pathlib.Path(output_directory)
    shell_path = output_directory / 'train.sh'
    base_dir = output_directory.parent.parent

    if shell_path.exists():
        shell_path.unlink()

    # Define the environment variables and the script commands
    script_content = f"""#!/bin/bash
set -e

export nnUNet_raw="{base_dir}/nnUNet_raw"
export nnUNet_preprocessed="{base_dir}/nnUNet_preprocessed"
export nnUNet_results="{base_dir}/nnUNet_trained_models"

nnUNet_plan_and_preprocess -t {dataset_id} --verify_dataset_integrity

for (( i=0; i<5; i++ ))
do
    nnUNet_train 3d_fullres nnUNetTrainerV2 {output_directory.name} $i --npz
done
"""

    # Write the script content to the file
    with open(shell_path, "w", newline="\n") as f:
        f.write(script_content)

# Code take from: https://github.com/MIC-DKFZ/nnUNet/blob/master/nnunetv2/dataset_conversion/generate_dataset_json.py

def generate_dataset_json(output_folder: str,
                          channel_names: dict,
                          labels: dict,
                          num_training_cases,
                          file_ending: str,
                          regions_class_order: Tuple[int, ...] = None,
                          dataset_name: str = None, reference: str = None, release: str = None, license: str = 'hands off!',
                          description: str = None,
                          overwrite_image_reader_writer: str = None, **kwargs):
    """
    Generates a dataset.json file in the output folder

    channel_names:
        Channel names must map the index to the name of the channel, example:
        {
            0: 'T1',
            1: 'CT'
        }
        Note that the channel names may influence the normalization scheme!! Learn more in the documentation.

    labels:
        This will tell nnU-Net what labels to expect. Important: This will also determine whether you use region-based training or not.
        Example regular labels:
        {
            'background': 0,
            'left atrium': 1,
            'some other label': 2
        }
        Example region-based training:
        {
            'background': 0,
            'whole tumor': (1, 2, 3),
            'tumor core': (2, 3),
            'enhancing tumor': 3
        }

        Remember that nnU-Net expects consecutive values for labels! nnU-Net also expects 0 to be background!

    num_training_cases: is used to double check all cases are there!

    file_ending: needed for finding the files correctly. IMPORTANT! File endings must match between images and
    segmentations!

    dataset_name, reference, release, license, description: self-explanatory and not used by nnU-Net. Just for
    completeness and as a reminder that these would be great!

    overwrite_image_reader_writer: If you need a special IO class for your dataset you can derive it from
    BaseReaderWriter, place it into nnunet.imageio and reference it here by name

    kwargs: whatever you put here will be placed in the dataset.json as well

    """

    has_regions: bool = any([isinstance(i, (tuple, list)) and len(i) > 1 for i in labels.values()])
    if has_regions:
        assert regions_class_order is not None, f"You have defined regions but regions_class_order is not set. " \
                                                f"You need that."
    # channel names need strings as keys
    keys = list(channel_names.keys())
    for k in keys:
        if not isinstance(k, str):
            channel_names[str(k)] = channel_names[k]
            del channel_names[k]

    # labels need ints as values
    for l in labels.keys():
        value = labels[l]
        if isinstance(value, (tuple, list)):
            value = tuple([int(i) for i in value])
            labels[l] = value
        else:
            labels[l] = int(labels[l])

    dataset_json = {
        'channel_names': channel_names,  # previously this was called 'modality'. I didn't like this so this is
        # channel_names now. Live with it.
        'labels': labels,
        'numTraining': num_training_cases,
        'file_ending': file_ending,
    }

    if dataset_name is not None:
        dataset_json['name'] = dataset_name
    if reference is not None:
        dataset_json['reference'] = reference
    if release is not None:
        dataset_json['release'] = release
    if license is not None:
        dataset_json['licence'] = license
    if description is not None:
        dataset_json['description'] = description
    if overwrite_image_reader_writer is not None:
        dataset_json['overwrite_image_reader_writer'] = overwrite_image_reader_writer
    if regions_class_order is not None:
        dataset_json['regions_class_order'] = regions_class_order

    dataset_json.update(kwargs)

    save_json(dataset_json, pathlib.Path(output_folder) / 'dataset.json', sort_keys=False)