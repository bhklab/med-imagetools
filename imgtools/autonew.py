import os, pathlib
import shutil
import glob
import pickle
import warnings

from typing import List

import numpy as np

from imgtools.utils import parser
import SimpleITK as sitk

from imgtools.ops import StructureSetToSegmentation, ImageAutoInput, ImageAutoOutput, Resample
from imgtools.pipeline import Pipeline
from imgtools.modules import Segmentation
from sklearn.model_selection import train_test_split

from imgtools.io.common import file_name_convention
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
                 output_directory,
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
                 label_names=None,
                 ignore_missing_regex=False):
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
            Whether to visualize the results of the pipeline using pyvis. Outputs to an HTML file.
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
        label_names: dict of str:str, default=None
            Dictionary representing the label that regexes are mapped to. For example, "GTV": "GTV.*" will combine all regexes that match "GTV.*" into "GTV"
        ignore_missing_regex: bool, default=False
            Whether to ignore missing regexes. Will raise an error if none of the regexes in label_names are found for a patient.
        """
        super().__init__(
            n_jobs=n_jobs,
            missing_strategy=missing_strategy,
            show_progress=show_progress,
            warn_on_error=warn_on_error)
        self.overwrite = overwrite
        # pipeline configuration
        self.input_directory = pathlib.Path(input_directory).as_posix()
        self.output_directory = pathlib.Path(output_directory).as_posix()
        self.spacing = spacing
        self.existing = [None] #self.existing_patients()
        self.is_nnunet = is_nnunet
        if is_nnunet:
            self.nnunet_info = {}
        else:
            self.nnunet_info = None
        self.train_size = train_size
        self.random_state = random_state
        self.label_names = label_names
        self.ignore_missing_regex = ignore_missing_regex

        if self.train_size == 1.0:
            warnings.warn("Train size is 1, all data will be used for training")
        
        if self.train_size == 0.0:
            warnings.warn("Train size is 0, all data will be used for testing")

        if self.train_size != 1 and not self.is_nnunet:
            warnings.warn("Cannot run train/test split without nnunet, ignoring train_size")

        if self.train_size > 1 or self.train_size < 0 and self.is_nnunet:
            raise ValueError("train_size must be between 0 and 1")
        
        if is_nnunet and (label_names is None or label_names == {}):
            raise ValueError("label_names must be provided for nnunet")
        

        if self.is_nnunet:
            self.nnunet_info["modalities"] = {"CT": "0000"} #modality to 4-digit code

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
        self.output = ImageAutoOutput(self.output_directory, self.output_streams, self.nnunet_info)

        #Make a directory
        if not os.path.exists(pathlib.Path(self.output_directory,".temp").as_posix()):
            os.mkdir(pathlib.Path(self.output_directory,".temp").as_posix())
        
        self.existing_roi_names = {}


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
        #Check if the subject_id has already been processed
        if os.path.exists(pathlib.Path(self.output_directory,".temp",f'temp_{subject_id}.pkl').as_posix()):
            print(f"{subject_id} already processed")
            return 

        print("Processing:", subject_id)

        read_results = self.input(subject_id)
        print(read_results)

        print(subject_id, " start")
        
        metadata = {}
        subject_modalities = set() # all the modalities that this subject has
        num_rtstructs = 0

        for i, colname in enumerate(self.output_streams):
            modality = colname.split("_")[0]
            subject_modalities.add(modality) #set add
            
            # Taking modality pairs if it exists till _{num}
            output_stream = ("_").join([item for item in colname.split("_") if item.isnumeric()==False])

            # If there are multiple connections existing, multiple connections means two modalities connected to one modality. They end with _1
            mult_conn = colname.split("_")[-1].isnumeric()
            num = colname.split("_")[-1]

            print(output_stream)

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
                    print(image.GetSize())
                image = self.resample(image)

                #update the metadata for this image
                if hasattr(read_results[i], "metadata") and read_results[i].metadata is not None:
                    metadata.update(read_results[i].metadata)

                #modality is MR and the user has selected to have nnunet output
                if self.is_nnunet:
                    if modality == "MR": #MR images can have various modalities like FLAIR, T1, etc.
                        self.nnunet_info['current_modality'] = metadata["AcquisitionContrast"]
                        if not metadata["AcquisitionContrast"] in self.nnunet_info["modalities"].keys(): #if the modality is new
                            self.nnunet_info["modalities"][metadata["AcquisitionContrast"]] = str(len(self.nnunet_info["modalities"])).zfill(4) #fill to 4 digits
                    else:
                        self.nnunet_info['current_modality'] = modality #CT
                    if "_".join(subject_id.split("_")[1::]) in self.train:
                        self.output(subject_id, image, output_stream, nnunet_info=self.nnunet_info)
                    else:
                        self.output(subject_id, image, output_stream, nnunet_info=self.nnunet_info, train_or_test="Ts")
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
                if not mult_conn:
                    self.output(subject_id, doses, output_stream)
                else:
                    self.output(f"{subject_id}_{num}", doses, output_stream)
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
                
                if mask is None: #ignored the missing regex
                    return

                for name in mask.roi_names.keys():
                    if name not in self.existing_roi_names.keys():
                        self.existing_roi_names[name] = len(self.existing_roi_names)
                mask.existing_roi_names = self.existing_roi_names

                # save output
                print(mask.GetSize())
                mask_arr = np.transpose(sitk.GetArrayFromImage(mask))
                
                if self.is_nnunet:
                    sparse_mask = mask.generate_sparse_mask().mask_array
                    sparse_mask = sitk.GetImageFromArray(sparse_mask) #convert the nparray to sitk image
                    if "_".join(subject_id.split("_")[1::]) in self.train:
                        self.output(subject_id, sparse_mask, output_stream, nnunet_info=self.nnunet_info, label_or_image="labels") #rtstruct is label for nnunet
                    else:
                        self.output(subject_id, sparse_mask, output_stream, nnunet_info=self.nnunet_info, label_or_image="labels", train_or_test="Ts")
                else:
                # if there is only one ROI, sitk.GetArrayFromImage() will return a 3d array instead of a 4d array with one slice
                    if len(mask_arr.shape) == 3:
                        mask_arr = mask_arr.reshape(1, mask_arr.shape[0], mask_arr.shape[1], mask_arr.shape[2])
                    
                    print(mask_arr.shape)
                    roi_names_list = list(mask.roi_names.keys())
                    for i in range(mask_arr.shape[0]):
                        new_mask = sitk.GetImageFromArray(np.transpose(mask_arr[i]))
                        new_mask.CopyInformation(mask)
                        new_mask = Segmentation(new_mask)
                        mask_to_process = new_mask
                        if not mult_conn:
                            # self.output(roi_names_list[i], mask_to_process, output_stream)
                            self.output(subject_id, mask_to_process, output_stream, True, roi_names_list[i])
                        else:
                            self.output(f"{subject_id}_{num}", mask_to_process, output_stream, True, roi_names_list[i])
                
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

                if not mult_conn:
                    self.output(subject_id, pet, output_stream)
                else:
                    self.output(f"{subject_id}_{num}", pet, output_stream)
                metadata[f"size_{output_stream}"] = str(pet.GetSize())
                metadata[f"metadata_{colname}"] = [read_results[i].get_metadata()]

                if hasattr(pet, "metadata") and pet.metadata is not None:
                    metadata.update(pet.metadata)

                print(subject_id, " SAVED PET")
            
            metadata[f"output_folder_{colname}"] = pathlib.Path(subject_id, colname).as_posix()
        #Saving all the metadata in multiple text files
        metadata["Modalities"] = str(list(subject_modalities))
        metadata["numRTSTRUCTs"] = num_rtstructs
        metadata["Train or Test"] = "train" if "_".join(subject_id.split("_")[1::]) in self.train else "test"
        with open(pathlib.Path(self.output_directory,".temp",f'{subject_id}.pkl').as_posix(),'wb') as f:
            pickle.dump(metadata,f)
        return 
    
    def save_data(self):
        files = glob.glob(pathlib.Path(self.output_directory, ".temp", "*.pkl").as_posix())
        for file in files:
            filename = pathlib.Path(file).name
            subject_id = os.path.splitext(filename)[0]
            with open(file,"rb") as f:
                metadata = pickle.load(f)
            self.output_df.loc[subject_id, list(metadata.keys())] = list(metadata.values())
        folder_renames = {}
        for col in self.output_df.columns:
            if col.startswith("folder"):
                self.output_df[col] = self.output_df[col].apply(lambda x: pathlib.Path(x).as_posix().split(self.input_directory)[1][1:]) # rel path, exclude the slash at the beginning
                folder_renames[col] = f"input_{col}"
        self.output_df.rename(columns=folder_renames, inplace=True) #append input_ to the column name
        self.output_df.to_csv(self.output_df_path)
        shutil.rmtree(pathlib.Path(self.output_directory, ".temp").as_posix())

    def run(self):
        """Execute the pipeline, possibly in parallel.
        """
        # Joblib prints progress to stdout if verbose > 50
        verbose = 51 if self.show_progress else 0

        subject_ids = self._get_loader_subject_ids()[:2]
        patient_ids = []
        for subject_id in subject_ids:
            if subject_id.split("_")[1::] not in patient_ids:
                patient_ids.append("_".join(subject_id.split("_")[1::]))
        if self.is_nnunet:
            self.train, self.test = train_test_split(patient_ids, train_size=self.train_size, random_state=self.random_state)
        else:
            self.train, self.test = [], []
        # Note that returning any SimpleITK object in process_one_subject is
        # not supported yet, since they cannot be pickled
        if os.path.exists(self.output_df_path) and not self.overwrite:
            print("Dataset already processed...")
            shutil.rmtree(pathlib.Path(self.output_directory, ".temp").as_posix())
        else:
            # Parallel(n_jobs=self.n_jobs, verbose=verbose)(
            #         delayed(self._process_wrapper)(subject_id) for subject_id in subject_ids)
            for subject_id in subject_ids:
                self._process_wrapper(subject_id)
            self.save_data()


def main():
    args = parser()
    pipeline = AutoPipeline(args.input_directory,
                            args.output_directory,
                            modalities=args.modalities,
                            spacing=args.spacing,
                            n_jobs=args.n_jobs,
                            visualize=args.visualize,
                            show_progress=args.show_progress)

    print(f'starting Pipeline...')
    pipeline.run()


    print(f'finished Pipeline!')

if __name__ == "__main__":
    main()

# if __name__ == "__main__":
#     pipeline = AutoPipeline(input_directory="C:/Users/qukev/BHKLAB/datasetshort/manifest-1598890146597/NSCLC-Radiomics-Interobserver1",
#                             output_directory="C:/Users/qukev/BHKLAB/autopipelineoutputshort",
#                             modalities="CT,RTSTRUCT",
#                             visualize=False,
#                             overwrite=True,
#                             generate_sparsemask=True,
#                             nnUnet_info={"study name": "NSCLC-Radiomics-Interobserver1"})

#     # pipeline = AutoPipeline(input_directory="C:/Users/qukev/BHKLAB/hnscc_testing/HNSCC",
#     #                         output_directory="C:/Users/qukev/BHKLAB/hnscc_testing_output",
#     #                         modalities="CT,RTSTRUCT",
#     #                         visualize=False,
#     #                         overwrite=True,
#     #                         generate_sparsemask=True)

#     # pipeline = AutoPipeline(input_directory="C:/Users/qukev/BHKLAB/dataset/manifest-1598890146597/NSCLC-Radiomics-Interobserver1",
#     #                         output_directory="C:/Users/qukev/BHKLAB/autopipelineoutput",
#     #                         modalities="CT,RTSTRUCT",
#     #                         visualize=False,
#     #                         overwrite=True,
#     #                         generate_sparsemask=True)

#     # pipeline = AutoPipeline(input_directory="C:/Users/qukev/BHKLAB/hnscc_pet/PET",
#     #                         output_directory="C:/Users/qukev/BHKLAB/hnscc_pet_output",
#     #                         modalities="CT,PT,RTDOSE",
#     #                         visualize=False,
#     #                         overwrite=True)

#     print(f'starting Pipeline...')
#     pipeline.run()


#     print(f'finished Pipeline!')