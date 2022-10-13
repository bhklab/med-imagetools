from aifc import Error
import os, pathlib
import shutil
import glob
import pickle
import struct
from attr import has
from matplotlib.style import available
import numpy as np
import sys
import warnings

from argparse import ArgumentParser
import yaml
import json
import SimpleITK as sitk

from imgtools.ops import StructureSetToSegmentation, ImageAutoInput, ImageAutoOutput, Resample
from imgtools.pipeline import Pipeline
from imgtools.utils.nnunet import generate_dataset_json, markdown_report_images
from imgtools.utils.args import parser
from joblib import Parallel, delayed
from imgtools.modules import Segmentation
from torch import sparse_coo_tensor
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import pandas as pd

from imgtools.io.common import file_name_convention
import dill
###############################################################
# Example usage:
# python radcure_simple.py ./data/RADCURE/data ./RADCURE_output
###############################################################


class AutoPipeline(Pipeline):
    """Example processing pipeline for the RADCURE dataset.
    This pipeline loads the CT images and structure sets, re-samples the images,
    and draws the GTV contour using the resampled image.
    """

    def __init__(self,
                 input_directory,
                 output_directory="",
                 modalities="CT",
                 spacing=(1., 1., 0.),
                 n_jobs=-1,
                 visualize=False,
                 missing_strategy="drop",
                 show_progress=False,
                 warn_on_error=False,
                 overwrite=False,
                 is_nnunet=False,
                 train_size=1.0,
                 random_state=42,
                 read_yaml_label_names=False,
                 ignore_missing_regex=False,
                 roi_yaml_path="",
                 custom_train_test_split=False,
                 is_nnunet_inference=False,
                 dataset_json_path="",
                 continue_processing=False,
                 dry_run=False,
                 verbose=False):
        """Initialize the pipeline.

        Parameters
        ----------
        input_directory: str
            Directory containing the input data
        output_directory: str
            Directory where the output data will be stored
        modalities: str, default="CT"
            Modalities to load. Can be a comma-separated list of modalities with no spaces
        spacing: tuple of floats, default=(1., 1., 0.)
            Spacing of the output image
        n_jobs: int, default=-1
            Number of jobs to run in parallel. If -1, use all cores
        visualize: bool, default=False
            Whether to visualize the results of the pipeline using pyvis. Outputs to an HTML file
        missing_strategy: str, default="drop"
            How to handle missing modalities. Can be "drop" or "fill"
        show_progress: bool, default=False
            Whether to show progress bars
        warn_on_error: bool, default=False
            Whether to warn on errors
        overwrite: bool, default=False
            Whether to write output files even if existing output files exist
        is_nnunet: bool, default=False
            Whether to format the output for nnunet
        train_size: float, default=1.0
            Proportion of the dataset to use for training, as a decimal
        random_state: int, default=42
            Random state for train_test_split
        read_yaml_label_names: bool, default=False
            Whether to read dictionary representing the label that regexes are mapped to from YAML. For example, "GTV": "GTV.*" will combine all regexes that match "GTV.*" into "GTV"
        ignore_missing_regex: bool, default=False
            Whether to ignore missing regexes. Will raise an error if none of the regexes in label_names are found for a patient
        roi_yaml_path: str, default=""
            The path to the yaml file defining regexes
        custom_train_test_split: bool, default=False
            Whether to use a custom train/test split. The remaining patients will be randomly split using train_size and random_state
        is_nnunet_inference: bool, default=False
            Whether to format the output for nnUNet inference
        dataset_json_path: str, default=""
            The path to the dataset.json file for nnUNet inference
        continue_processing: bool, default=False
            Whether to continue processing a partially processed dataset
        dry_run: bool, default=False
            Whether to run the pipeline without writing any output files
        """

        #save all the arguments to a pkl file and then load them back if there is a continue processing flag

        self.continue_processing = continue_processing
        self.dry_run = dry_run
        self.v = verbose

        if dry_run:
            is_nnunet = False
            is_nnunet_inference = False

        if dry_run and continue_processing:
            raise ValueError("Cannot continue processing a dry run. Set --continue_processing to False to do a dry run.")

        if not dry_run and output_directory == "":
            raise ValueError("Must specify an output directory")
        # pipeline configuration
        if not os.path.isabs(input_directory):
            input_directory = pathlib.Path(os.getcwd(), input_directory).as_posix()
        else:
            input_directory = pathlib.Path(input_directory).as_posix()  # consistent parsing. ensures last child directory doesn't end with slash
        
        if not os.path.isabs(output_directory):
            output_directory = pathlib.Path(os.getcwd(), output_directory).as_posix()
        else:
            output_directory = pathlib.Path(output_directory).as_posix() # consistent parsing. ensures last child directory doesn't end with slash

        if not os.path.exists(output_directory):
            # raise FileNotFoundError(f"Output directory {output_directory} does not exist")
            os.makedirs(output_directory)
        if not os.path.exists(input_directory):
            raise FileNotFoundError(f"Input directory {input_directory} does not exist")
        
        self.input_directory = pathlib.Path(input_directory).as_posix()
        self.output_directory = pathlib.Path(output_directory).as_posix()
        
        if not is_nnunet and continue_processing and not os.path.exists(pathlib.Path(output_directory, ".temp").as_posix()):
            raise FileNotFoundError(f"Cannot continue processing. .temp directory does not exist in {output_directory}. Run without --continue_processing to start from scratch.")

        study_name = os.path.split(self.input_directory)[1]
        if is_nnunet_inference:
            roi_yaml_path = ""
            custom_train_test_split = False
            is_nnunet = False
            if modalities != "CT" or modalities != "MR":
                raise ValueError("nnUNet inference can only be run on image files. Please set modalities to 'CT' or 'MR'")
        if is_nnunet:
            self.base_output_directory = self.output_directory
            if not os.path.exists(pathlib.Path(self.output_directory, "nnUNet_preprocessed").as_posix()):
                os.makedirs(pathlib.Path(self.output_directory, "nnUNet_preprocessed").as_posix())
            if not os.path.exists(pathlib.Path(self.output_directory, "nnUNet_trained_models").as_posix()):
                os.makedirs(pathlib.Path(self.output_directory, "nnUNet_trained_models").as_posix())
            self.output_directory = pathlib.Path(self.output_directory, "nnUNet_raw_data_base",
            "nnUNet_raw_data").as_posix()
            if not os.path.exists(self.output_directory):
                os.makedirs(self.output_directory)
            all_nnunet_folders = glob.glob(pathlib.Path(self.output_directory, "*", " ").as_posix())
            # print(all_nnunet_folders)
            numbers = [int(os.path.split(os.path.split(folder)[0])[1][4:7]) for folder in all_nnunet_folders if os.path.split(os.path.split(folder)[0])[1].startswith("Task")]
            # print(numbers, continue_processing)
            if (len(numbers) == 0 and continue_processing) or not continue_processing or not os.path.exists(pathlib.Path(self.output_directory, f"Task{max(numbers)}_{study_name}", ".temp").as_posix()):
                available_numbers = list(range(500, 1000))
                for folder in all_nnunet_folders:
                    folder_name = os.path.split(os.path.split(folder)[0])[1]
                    if folder_name.startswith("Task") and folder_name[4:7].isnumeric() and int(folder_name[4:7]) in available_numbers:
                        available_numbers.remove(int(folder_name[4:7]))
                if len(available_numbers) == 0:
                    raise Error("There are not enough task ID's for the nnUNet output. Please make sure that there is at least one task ID available between 500 and 999, inclusive")
                task_folder_name = f"Task{available_numbers[0]}_{study_name}"
                self.output_directory = pathlib.Path(self.output_directory, task_folder_name).as_posix()
                self.task_id = available_numbers[0]
            else:
                self.task_id = max(numbers)
                task_folder_name = f"Task{self.task_id}_{study_name}"
                self.output_directory = pathlib.Path(self.output_directory, task_folder_name).as_posix()
            if not os.path.exists(pathlib.Path(self.output_directory, ".temp").as_posix()):
                os.makedirs(pathlib.Path(self.output_directory, ".temp").as_posix())
        
        if not dry_run:
            #Make a directory
            if not os.path.exists(pathlib.Path(self.output_directory,".temp").as_posix()):
                os.mkdir(pathlib.Path(self.output_directory,".temp").as_posix())
                
            with open(pathlib.Path(self.output_directory, ".temp", "init_parameters.pkl").as_posix(), "wb") as f:
                parameters = locals() #save all the parameters in case we need to continue processing
                dill.dump(parameters, f)

            #continue processing operations
            self.finished_subjects = [pathlib.Path(e).name[:-4] for e in glob.glob(pathlib.Path(self.output_directory, ".temp", "*.pkl").as_posix())] #remove the .pkl
            if continue_processing:
                with open(pathlib.Path(self.output_directory, ".temp", "init_parameters.pkl").as_posix(), "rb") as f:
                    parameters = dill.load(f)
                    input_directory = parameters["input_directory"]
                    output_directory = parameters["output_directory"]
                    modalities = parameters["modalities"]
                    spacing = parameters["spacing"]
                    n_jobs = parameters["n_jobs"]
                    visualize = parameters["visualize"]
                    missing_strategy = parameters["missing_strategy"]
                    show_progress = parameters["show_progress"]
                    warn_on_error = parameters["warn_on_error"]
                    overwrite = parameters["overwrite"]
                    is_nnunet = parameters["is_nnunet"]
                    train_size = parameters["train_size"]
                    random_state = parameters["random_state"]
                    read_yaml_label_names = parameters["read_yaml_label_names"]
                    ignore_missing_regex = parameters["ignore_missing_regex"]
                    roi_yaml_path = parameters["roi_yaml_path"]
                    custom_train_test_split = parameters["custom_train_test_split"]
                    is_nnunet_inference = parameters["is_nnunet_inference"]
                    dataset_json_path = parameters["dataset_json_path"]

        super().__init__(
            n_jobs=n_jobs,
            missing_strategy=missing_strategy,
            show_progress=show_progress,
            warn_on_error=warn_on_error)
        self.overwrite = overwrite
        self.spacing = spacing
        self.existing = [None] #self.existing_patients()
        self.is_nnunet = is_nnunet
        if is_nnunet or is_nnunet_inference:
            self.nnunet_info = {}
        else:
            self.nnunet_info = None
        self.train_size = train_size
        self.random_state = random_state
        self.label_names = {}
        self.ignore_missing_regex = ignore_missing_regex
        self.custom_train_test_split = custom_train_test_split
        self.is_nnunet_inference = is_nnunet_inference

        if roi_yaml_path != "" and not read_yaml_label_names:
            warnings.warn("The YAML will not be read since it has not been specified to read them. To use the file, run the CLI with --read_yaml_label_names")

        roi_path = pathlib.Path(self.input_directory, "roi_names.yaml").as_posix() if roi_yaml_path == "" else roi_yaml_path
        if read_yaml_label_names:
            if os.path.exists(roi_path):
                with open(roi_path, "r") as f:
                    try:
                        self.label_names = yaml.safe_load(f)
                    except yaml.YAMLError as exc:
                        print(exc)
            else:
                raise FileNotFoundError(f"No file named roi_names.yaml found at {roi_path}. If you did not intend on creating ROI regexes, run the CLI without --read_yaml_label_names")
        
        if not isinstance(self.label_names, dict):
            raise ValueError("roi_names.yaml must parse as a dictionary")

        for k, v in self.label_names.items():
            if not isinstance(v, list) and not isinstance(v, str):
                raise ValueError(f"Label values must be either a list of strings or a string. Got {v} for {k}")
            elif isinstance(v, list):
                for a in v:
                    if not isinstance(a, str):
                        raise ValueError(f"Label values must be either a list of strings or a string. Got {a} in list {v} for {k}")
            elif not isinstance(k, str):
                raise ValueError(f"Label names must be a string. Got {k} for {v}")

        if self.train_size == 1.0 and is_nnunet:
            warnings.warn("Train size is 1, all data will be used for training")
        
        if self.train_size == 0.0 and is_nnunet:
            warnings.warn("Train size is 0, all data will be used for testing")

        if self.train_size != 1 and not self.is_nnunet:
            warnings.warn("Cannot run train/test split without nnunet, ignoring train_size")

        if self.train_size > 1 or self.train_size < 0 and self.is_nnunet:
            raise ValueError("train_size must be between 0 and 1")
        
        if is_nnunet and (not read_yaml_label_names or self.label_names == {}):
            raise ValueError("YAML label names must be provided for nnunet")
        
        if custom_train_test_split and not is_nnunet:
            raise ValueError("Cannot use custom train/test split without nnunet")

        custom_train_test_split_path = pathlib.Path(self.input_directory, "custom_train_test_split.yaml").as_posix()
        if custom_train_test_split and is_nnunet:
            if os.path.exists(custom_train_test_split_path):
                with open(custom_train_test_split_path, "r") as f:
                    try:
                        self.custom_split = yaml.safe_load(f)
                        if isinstance(self.custom_split, list):
                            for e in self.custom_split:
                                if not isinstance(e, str):
                                    raise ValueError("Custom split must be a list of strings. Place quotes around patient ID's that don't parse as YAML strings")
                            self.custom_split = {"train": [], "test": self.custom_split}
                        if isinstance(self.custom_split, dict):
                            if sorted(list(self.custom_split.keys())) != ["test", "train"] and list(self.custom_split.keys()) != ["train"] and list(self.custom_split.keys()) != ["test"]:
                                raise ValueError("Custom split must be a dictionary with keys 'train' and 'test'")
                            for k, v in self.custom_split.items():
                                if not isinstance(v, list):
                                    raise ValueError(f"Custom split must be a list of strings. Place quotes around patient ID's that don't parse as YAML strings. Got {v} for {k}")
                                for e in v:
                                    if not isinstance(e, str):
                                        raise ValueError("Custom split must be a list of strings. Place quotes around patient ID's that don't parse as YAML strings")
                            if list(self.custom_split.keys()) == ["train"]:
                                self.custom_split = {"train": self.custom_split["train"], "test": []}
                            elif list(self.custom_split.keys()) == ["test"]:
                                self.custom_split = {"train": [], "test": self.custom_split["test"]}
                        for e in self.custom_split["train"]:
                            if e in self.custom_split["test"]:
                                raise ValueError("Custom split cannot contain the same patient ID in both train and test")
                    except yaml.YAMLError as exc:
                        print(exc)
            else:
                raise FileNotFoundError(f"No file named custom_train_test_split.yaml found at {custom_train_test_split_path}. If you did not intend on creating a custom train-test-split, run the CLI without --custom_train_test_split")

        if self.is_nnunet:
            self.nnunet_info["modalities"] = {"CT": "0000"} #modality to 4-digit code

        if is_nnunet_inference:
            if not os.path.exists(dataset_json_path):
                raise FileNotFoundError(f"No file named {dataset_json_path} found. Image modality definitions are required for nnUNet inference")
            else:
                with open(dataset_json_path, "r") as f:
                    self.nnunet_info["modalities"] = {v: k.zfill(4) for k, v in json.load(f)["modality"].items()}

        #input operations
        self.input = ImageAutoInput(input_directory, modalities, n_jobs, visualize)
        
        self.output_df_path = pathlib.Path(self.output_directory, "dataset.csv").as_posix()
        #Output component table
        self.output_df = self.input.df_combined
        #Name of the important columns which needs to be saved    
        self.output_streams = self.input.output_streams
        
        # image processing ops
        self.resample = Resample(spacing=self.spacing)
        self.make_binary_mask = StructureSetToSegmentation(roi_names=self.label_names, continuous=False) # "GTV-.*"

        # output ops
        self.output = ImageAutoOutput(self.output_directory, self.output_streams, self.nnunet_info, self.is_nnunet_inference)
        
        self.existing_roi_names = {"background": 0}
        # self.existing_roi_names.update({k:i+1 for i, k in enumerate(self.label_names.keys())})
        if is_nnunet or is_nnunet_inference:
            self.total_modality_counter = {}
            self.patients_with_missing_labels = set()
        

    def glob_checker_nnunet(self, subject_id):
        folder_names = ["imagesTr", "labelsTr", "imagesTs", "labelsTs"]
        files = []
        for folder_name in folder_names:
            if os.path.exists(pathlib.Path(self.input_directory, folder_name).as_posix()):
                files.extend(glob.glob(pathlib.Path(self.output_directory,folder_name,"*.nii.gz").as_posix()))
        for f in files:
            if f.startswith(subject_id):
                return True
        return False

    def process_one_subject(self, subject_id):
        """Define the processing operations for one subject.
        This method must be defined for all pipelines. It is used to define
        the preprocessing steps for a single subject (note: that might mean
        multiple images, structures, etc.). During pipeline execution, this
        method will receive one argument, subject_id, which can be used to
        retrieve inputs and save outputs.

        Parameters
        ----------
        subject_id : str
           The ID of subject to process
        """
        if self.continue_processing:
            if subject_id in self.finished_subjects:
                return
        # if we want overwriting or if we don't want it and the file doesn't exist, we can process
        if self.overwrite or (not self.overwrite and not (os.path.exists(pathlib.Path(self.output_directory, subject_id).as_posix()) or self.glob_checker_nnunet(subject_id))):
            #Check if the subject_id has already been processed
            if os.path.exists(pathlib.Path(self.output_directory,".temp",f'temp_{subject_id}.pkl').as_posix()):
                print(f"{subject_id} already processed")
                return

            print("Processing:", subject_id)

            read_results = self.input(subject_id)
            # print(read_results)

            print(subject_id, " start")
            
            metadata = {}
            subject_modalities = set() # all the modalities that this subject has
            num_rtstructs = 0

            for i, colname in enumerate(self.output_streams): #sorted(self.output_streams)): #CT comes before MR before PT before RTDOSE before RTSTRUCT
                modality = colname.split("_")[0]
                subject_modalities.add(modality) #set add
                
                # Taking modality pairs if it exists till _{num}
                output_stream = ("_").join([item for item in colname.split("_") if item.isnumeric()==False])

                # If there are multiple connections existing, multiple connections means two modalities connected to one modality. They end with _1
                mult_conn = colname.split("_")[-1].isnumeric()
                num = colname.split("_")[-1]

                if self.v:
                    print("output_stream:", output_stream)

                if read_results[i] is None:
                    print("The subject id: {} has no {}".format(subject_id, colname))
                    pass
                elif modality == "CT" or modality == 'MR':
                    image = read_results[i].image
                    if len(image.GetSize()) == 4:
                        assert image.GetSize()[-1] == 1, f"There is more than one volume in this CT file for {subject_id}."
                        extractor = sitk.ExtractImageFilter()
                        extractor.SetSize([*image.GetSize()[:3], 0])
                        extractor.SetIndex([0, 0, 0, 0])    
                        
                        image = extractor.Execute(image)
                        if self.v:
                            print("image.GetSize():", image.GetSize())
                    try:
                        image = self.resample(image)
                    except Exception as e:
                        print(e)
                        warnings.warn("Could not resample {} for subject {}".format(colname, subject_id))

                    #update the metadata for this image
                    if hasattr(read_results[i], "metadata") and read_results[i].metadata is not None:
                        metadata.update(read_results[i].metadata)

                    #modality is MR and the user has selected to have nnunet output
                    if self.is_nnunet:
                        if modality == "MR": #MR images can have various modalities like FLAIR, T1, etc.
                            if not metadata["AcquisitionContrast"] in self.total_modality_counter.keys():
                                self.total_modality_counter[metadata["AcquisitionContrast"]] = 1
                            else:
                                self.total_modality_counter[metadata["AcquisitionContrast"]] += 1
                            self.nnunet_info['current_modality'] = metadata["AcquisitionContrast"]
                            if not metadata["AcquisitionContrast"] in self.nnunet_info["modalities"].keys(): #if the modality is new
                                self.nnunet_info["modalities"][metadata["AcquisitionContrast"]] = str(len(self.nnunet_info["modalities"])).zfill(4) #fill to 4 digits
                        else:
                            self.nnunet_info['current_modality'] = modality #CT
                            if not modality in self.total_modality_counter.keys():
                                self.total_modality_counter[modality] = 1
                            else:
                                self.total_modality_counter[modality] += 1
                        if "_".join(subject_id.split("_")[1::]) in self.train:
                            self.output(subject_id, image, output_stream, nnunet_info=self.nnunet_info)
                        else:
                            self.output(subject_id, image, output_stream, nnunet_info=self.nnunet_info, train_or_test="Ts")
                    elif self.is_nnunet_inference:
                        self.nnunet_info["current_modality"] = modality if modality == "CT" else metadata["AcquisitionContrast"]
                        if not self.nnunet_info["current_modality"] in self.nnunet_info["modalities"].keys():
                            raise ValueError(f"The modality {self.nnunet_info['current_modality']} is not in the list of modalities that are present in dataset.json.")
                        self.output(subject_id, image, output_stream, nnunet_info=self.nnunet_info)
                    else:
                        self.output(subject_id, image, output_stream)

                    metadata[f"size_{output_stream}"] = str(image.GetSize())


                    print(subject_id, " SAVED IMAGE")
                elif modality == "RTDOSE":
                    try: #For cases with no image present
                        doses = read_results[i].resample_dose(image)
                    except:
                        Warning("No CT image present. Returning dose image without resampling")
                        doses = read_results[i]
                    
                    # save output
                    self.output(subject_id, doses, output_stream)
                    metadata[f"size_{output_stream}"] = str(doses.GetSize())
                    metadata[f"metadata_{colname}"] = [read_results[i].get_metadata()]

                    if hasattr(doses, "metadata") and doses.metadata is not None:
                        metadata.update(doses.metadata)

                    print(subject_id, " SAVED DOSE")
                elif modality == "RTSTRUCT":
                    num_rtstructs += 1
                    #For RTSTRUCT, you need image or PT
                    structure_set = read_results[i]
                    conn_to = output_stream.split("_")[-1]

                    # make_binary_mask relative to ct/pet
                    if conn_to == "CT" or conn_to == "MR":
                        mask = self.make_binary_mask(structure_set, image, self.existing_roi_names, self.ignore_missing_regex)
                    elif conn_to == "PT":
                        mask = self.make_binary_mask(structure_set, pet, self.existing_roi_names, self.ignore_missing_regex)
                    else:
                        raise ValueError("You need to pass a reference CT or PT/PET image to map contours to.")
                    
                    if mask is None: #ignored the missing regex, and exit the loop
                        if self.is_nnunet:
                            image_test_path = pathlib.Path(self.output_directory, "imagesTs").as_posix()
                            image_train_path = pathlib.Path(self.output_directory, "imagesTr").as_posix()
                            if os.path.exists(image_test_path):
                                all_files = glob.glob(pathlib.Path(image_test_path, "*.nii.gz").as_posix())
                                # print(all_files)
                                for file in all_files:
                                    if subject_id in os.path.split(file)[1]:
                                        os.remove(file)
                            if os.path.exists(image_train_path):
                                all_files = glob.glob(pathlib.Path(image_train_path, "*.nii.gz").as_posix())
                                # print(all_files)
                                for file in all_files:
                                    if subject_id in os.path.split(file)[1]:
                                        os.remove(file)
                            warnings.warn(f"Patient {subject_id} is missing a complete image-label pair")
                            self.patients_with_missing_labels.add("".join(subject_id.split("_")[1:]))
                            return
                        else:
                            break
                    
                    for name in mask.roi_names.keys():
                        if name not in self.existing_roi_names.keys():
                            self.existing_roi_names[name] = len(self.existing_roi_names)
                    mask.existing_roi_names = self.existing_roi_names

                    
                    if self.v:
                        print("mask.GetSize():", mask.GetSize())
                    mask_arr = np.transpose(sitk.GetArrayFromImage(mask))
                    
                    if self.is_nnunet:
                        sparse_mask = np.transpose(mask.generate_sparse_mask().mask_array)
                        sparse_mask = sitk.GetImageFromArray(sparse_mask) #convert the nparray to sitk image
                        sparse_mask.CopyInformation(image)
                        if "_".join(subject_id.split("_")[1::]) in self.train:
                            self.output(subject_id, sparse_mask, output_stream, nnunet_info=self.nnunet_info, label_or_image="labels") #rtstruct is label for nnunet
                        else:
                            self.output(subject_id, sparse_mask, output_stream, nnunet_info=self.nnunet_info, label_or_image="labels", train_or_test="Ts")
                    else:
                    # if there is only one ROI, sitk.GetArrayFromImage() will return a 3d array instead of a 4d array with one slice
                        if len(mask_arr.shape) == 3:
                            mask_arr = mask_arr.reshape(1, mask_arr.shape[0], mask_arr.shape[1], mask_arr.shape[2])
                        
                        if self.v:
                            print(mask_arr.shape)

                        roi_names_list = list(mask.roi_names.keys())
                        for i in range(mask_arr.shape[0]):
                            new_mask = sitk.GetImageFromArray(np.transpose(mask_arr[i]))
                            new_mask.CopyInformation(mask)
                            new_mask = Segmentation(new_mask)
                            mask_to_process = new_mask
                            
                            # output
                            self.output(subject_id, mask_to_process, output_stream, True, roi_names_list[i])
                    
                    if hasattr(structure_set, "metadata") and structure_set.metadata is not None:
                        metadata.update(structure_set.metadata)

                    metadata[f"metadata_{colname}"] = [structure_set.roi_names]

                    print(subject_id, "SAVED MASK ON", conn_to)
                elif modality == "PT":
                    try:
                        #For cases with no image present
                        pet = read_results[i].resample_pet(image)
                    except:
                        Warning("No CT image present. Returning PT/PET image without resampling.")
                        pet = read_results[i]

                    # output
                    self.output(subject_id, pet, output_stream)
                    metadata[f"size_{output_stream}"] = str(pet.GetSize())
                    metadata[f"metadata_{colname}"] = [read_results[i].get_metadata()]

                    if hasattr(pet, "metadata") and pet.metadata is not None:
                        metadata.update(pet.metadata)

                    print(subject_id, " SAVED PET")
                
                metadata[f"output_folder_{colname}"] = pathlib.Path(subject_id, colname).as_posix()
            #Saving all the metadata in multiple text files
            metadata["Modalities"] = str(list(subject_modalities))
            metadata["numRTSTRUCTs"] = num_rtstructs
            if self.is_nnunet:
                metadata["Train or Test"] = "train" if "_".join(subject_id.split("_")[1::]) in self.train else "test"
            with open(pathlib.Path(self.output_directory,".temp",f'{subject_id}.pkl').as_posix(),'wb') as f: #the continue flag depends on this being the last line in this method
                pickle.dump(metadata,f)
            return 
    
    def save_data(self):
        files = glob.glob(pathlib.Path(self.output_directory, ".temp", "*.pkl").as_posix())
        for file in files:
            filename = pathlib.Path(file).name
            if filename == "init_parameters.pkl":
                continue
            subject_id = os.path.splitext(filename)[0]
            with open(file,"rb") as f:
                metadata = pickle.load(f)
                # print("sadf123", metadata)
            np.warnings.filterwarnings('ignore', category=np.VisibleDeprecationWarning)
            self.output_df.loc[subject_id, list(metadata.keys())] = list(metadata.values()) #subject id targets the rows with that subject id and it is reassigning all the metadata values by key
            # pd.set_option('display.max_rows', None)
            # pd.set_option('display.max_columns', None)
            # pd.set_option('display.width', None)
            # print("asdfjlkasdjfkajfshg", self.output_df.head())
        folder_renames = {}
        for col in self.output_df.columns:
            if col.startswith("folder"):
                self.output_df[col] = self.output_df[col].apply(lambda x: x if not isinstance(x, str) else pathlib.Path(x).as_posix().split(self.input_directory)[1][1:]) # rel path, exclude the slash at the beginning
                folder_renames[col] = f"input_{col}"
        self.output_df.rename(columns=folder_renames, inplace=True) #append input_ to the column name
        # print("df in autopipe")
        # print(self.output_df.iloc[0])
        self.output_df.to_csv(self.output_df_path) #dataset.csv

        shutil.rmtree(pathlib.Path(self.output_directory, ".temp").as_posix())

        if self.is_nnunet: #dataset.json for nnunet and .sh file to run to process it
            imagests_path = pathlib.Path(self.output_directory, "imagesTs").as_posix()
            images_test_location = imagests_path if os.path.exists(imagests_path) else None
            # print(self.existing_roi_names)
            generate_dataset_json(pathlib.Path(self.output_directory, "dataset.json").as_posix(),
                                pathlib.Path(self.output_directory, "imagesTr").as_posix(),
                                images_test_location,
                                tuple(self.nnunet_info["modalities"].keys()),
                                {v:k for k, v in self.existing_roi_names.items()},
                                os.path.split(self.input_directory)[1])
            _, child = os.path.split(self.output_directory)
            shell_path = pathlib.Path(self.output_directory, child.split("_")[1]+".sh").as_posix()
            if os.path.exists(shell_path):
                os.remove(shell_path)
            with open(shell_path, "w", newline="\n") as f:
                output = "#!/bin/bash\n"
                output += "set -e"
                output += f'export nnUNet_raw_data_base="{self.base_output_directory}/nnUNet_raw_data_base"\n'
                output += f'export nnUNet_preprocessed="{self.base_output_directory}/nnUNet_preprocessed"\n'
                output += f'export RESULTS_FOLDER="{self.base_output_directory}/nnUNet_trained_models"\n\n'
                output += f'nnUNet_plan_and_preprocess -t {self.task_id} --verify_dataset_integrity\n\n'
                output += 'for (( i=0; i<5; i++ ))\n'
                output += 'do\n'
                output += f'    nnUNet_train 3d_fullres nnUNetTrainerV2 {os.path.split(self.output_directory)[1]} $i --npz\n'
                output += 'done'
                f.write(output)
            markdown_report_images(self.output_directory, self.total_modality_counter) #images saved to the output directory
        markdown_path = pathlib.Path(self.output_directory, "report.md").as_posix()
        with open(markdown_path, "w", newline="\n") as f:
            output = "# Dataset Report\n\n"
            if not self.is_nnunet:
                output += "## Patients with broken DICOM references\n\n"
                output += "<details>\n"
                output += "\t<summary>Click to see the list of patients with broken DICOM references</summary>\n\n\t"
                formatted_list = "\n\t".join(self.broken_patients)
                output += f"{formatted_list}\n"
                output += "</details>\n\n"
            if self.is_nnunet:
                output += "## Train Test Split\n\n"
                # pie_path = pathlib.Path(self.output_directory, "markdown_images", "nnunet_train_test_pie.png").as_posix()
                pie_path = pathlib.Path("markdown_images", "nnunet_train_test_pie.png").as_posix()
                output += f"![Pie Chart of Train Test Split]({pie_path})\n\n"
                output += "## Image Modality Distribution\n\n"
                # bar_path = pathlib.Path(self.output_directory, "markdown_images", "nnunet_modality_count.png").as_posix()
                bar_path = pathlib.Path("markdown_images", "nnunet_modality_count.png").as_posix()
                output += f"![Pie Chart of Image Modality Distribution]({bar_path})\n\n"
            f.write(output)



    def run(self):
        """Execute the pipeline, possibly in parallel.
        """
        # Joblib prints progress to stdout if verbose > 50
        verbose = 51 if self.v or self.show_progress else 0

        subject_ids = self._get_loader_subject_ids()
        patient_ids = []
        if not self.dry_run:
            for subject_id in subject_ids:
                if subject_id.split("_")[1::] not in patient_ids:
                    patient_ids.append("_".join(subject_id.split("_")[1::]))
            if self.is_nnunet:
                custom_train = []
                custom_test = []
                if self.custom_train_test_split:
                    patient_ids = [item for item in patient_ids if item not in self.custom_split["train"] and item not in self.custom_split["test"]]
                    custom_test = self.custom_split["test"]
                    custom_train = self.custom_split["train"]
                if self.train_size == 1:
                    self.train = patient_ids
                    self.test = []
                    self.train.extend(custom_train)
                    self.test.extend(custom_test)
                else:
                    self.train, self.test = train_test_split(sorted(patient_ids), train_size=self.train_size, random_state=self.random_state)
                    self.train.extend(custom_train)
                    self.test.extend(custom_test)
            else:
                self.train, self.test = [], []
            # Note that returning any SimpleITK object in process_one_subject is
            # not supported yet, since they cannot be pickled
            if os.path.exists(self.output_df_path) and not self.overwrite:
                print("Dataset already processed...")
                shutil.rmtree(pathlib.Path(self.output_directory, ".temp").as_posix())
            else:
                Parallel(n_jobs=self.n_jobs, verbose=verbose, require='sharedmem')(
                        delayed(self._process_wrapper)(subject_id) for subject_id in subject_ids)
                # for subject_id in subject_ids:
                #     self._process_wrapper(subject_id)
                self.broken_patients = []
                if not self.is_nnunet:
                    all_patient_names = glob.glob(pathlib.Path(self.input_directory, "*"," ").as_posix()[0:-1])
                    all_patient_names = [os.path.split(os.path.split(x)[0])[1] for x in all_patient_names]
                    for e in all_patient_names:
                        if e not in patient_ids:
                            warnings.warn(f"Patient {e} does not have proper DICOM references")
                            self.broken_patients.append(e)
                self.save_data()

def main():
    args = parser()
    print('initializing AutoPipeline...')
    pipeline = AutoPipeline(args.input_directory,
                            args.output_directory,
                            modalities=args.modalities,
                            visualize=args.visualize,
                            spacing=args.spacing,
                            n_jobs=args.n_jobs,
                            show_progress=args.show_progress,
                            warn_on_error=args.warn_on_error,
                            overwrite=args.overwrite,
                            is_nnunet=args.nnunet,
                            train_size=args.train_size,
                            random_state=args.random_state,
                            read_yaml_label_names=args.read_yaml_label_names,
                            ignore_missing_regex=args.ignore_missing_regex,
                            roi_yaml_path=args.roi_yaml_path,
                            custom_train_test_split=args.custom_train_test_split,
                            is_nnunet_inference=args.is_nnunet_inference,
                            dataset_json_path=args.dataset_json_path,
                            continue_processing=args.continue_processing,
                            dry_run=args.dry_run,
                            verbose=args.verbose)
    if not args.dry_run:
        print(f'starting AutoPipeline...')
        pipeline.run()


        print('finished AutoPipeline!')
    else:
        print('dry run complete, no processing done')
    
    """Print general summary info"""

    """Print nnU-Net specific info here:
    * dataset.json can be found at /path/to/dataset/json
    * You can train nnU-Net by cloning /path/to/nnunet/repo and run `nnUNet_plan_and_preprocess -t taskID` to let the nnU-Net package prepare 
    """
    print(f"Outputted data to {args.output_directory}")
    csv_path = pathlib.Path(args.output_directory, "dataset.csv").as_posix()
    print(f"Dataset info found at {csv_path}")
    if args.nnunet:
        json_path = pathlib.Path(args.output_directory, "dataset.json").as_posix()
        print(f"dataset.json for nnU-net can be found at {json_path}")
        print("You can train nnU-net by cloning https://github.com/MIC-DKFZ/nnUNet/ and run `nnUNet_plan_and_preprocess -t taskID` to let the nnU-Net package prepare")

if __name__ == "__main__":
    main()
