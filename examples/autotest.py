import os, pathlib
import shutil
import glob
import pickle
import numpy as np
import sys

from argparse import ArgumentParser
import SimpleITK as sitk

from imgtools.ops import StructureSetToSegmentation, ImageAutoInput, ImageAutoOutput, Resample
from imgtools.pipeline import Pipeline
from joblib import Parallel, delayed
from imgtools.modules import Segmentation
from torch import sparse_coo_tensor

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
                 overwrite=False):

        super().__init__(
            n_jobs=n_jobs,
            missing_strategy=missing_strategy,
            show_progress=show_progress,
            warn_on_error=warn_on_error)
        self.overwrite = overwrite
        # pipeline configuration
        self.input_directory = input_directory
        self.output_directory = output_directory
        self.spacing = spacing
        self.existing = [None] #self.existing_patients()

        #input operations
        self.input = ImageAutoInput(input_directory, modalities, n_jobs, visualize)
        
        self.output_df_path = pathlib.Path(self.output_directory, "dataset.csv").as_posix()
        #Output component table
        self.output_df = self.input.df_combined
        #Name of the important columns which needs to be saved    
        self.output_streams = self.input.output_streams
        
        # image processing ops
        self.resample = Resample(spacing=self.spacing)
        self.make_binary_mask = StructureSetToSegmentation(roi_names=[], continuous=False) # "GTV-.*"

        # output ops
        self.output = ImageAutoOutput(self.output_directory, self.output_streams)

        #Make a directory
        if not os.path.exists(pathlib.Path(self.output_directory,".temp").as_posix()):
            os.mkdir(pathlib.Path(self.output_directory,".temp").as_posix())


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
        for i, colname in enumerate(self.output_streams):
            modality = colname.split("_")[0]

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
                image = read_results[i]
                if len(image.GetSize()) == 4:
                    assert image.GetSize()[-1] == 1, f"There is more than one volume in this CT file for {subject_id}."
                    extractor = sitk.ExtractImageFilter()
                    extractor.SetSize([*image.GetSize()[:3], 0])
                    extractor.SetIndex([0, 0, 0, 0])    
                    
                    image = extractor.Execute(image)
                    print(image.GetSize())
                image = self.resample(image)
                #Saving the output
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
                print(subject_id, " SAVED DOSE")
            elif modality == "RTSTRUCT":
                #For RTSTRUCT, you need image or PT
                structure_set = read_results[i]
                conn_to = output_stream.split("_")[-1]

                # make_binary_mask relative to ct/pet
                if conn_to == "CT" or conn_to == "MR":
                    mask = self.make_binary_mask(structure_set, image)
                elif conn_to == "PT":
                    mask = self.make_binary_mask(structure_set, pet)
                else:
                    raise ValueError("You need to pass a reference CT or PT/PET image to map contours to.")
                
                # save output
                print(mask.GetSize())
                mask_arr = np.transpose(sitk.GetArrayFromImage(mask))

                
                # sparse_mask = mask.generate_sparse_mask()


                # np.set_printoptions(threshold=sys.maxsize)
                # print(sparse_mask.mask_array.shape)
                # print(sparse_mask.mask_array[350:360,290:300,93])
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
                print(subject_id, " SAVED PET")
        #Saving all the metadata in multiple text files
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
        self.output_df.to_csv(self.output_df_path)
        shutil.rmtree(pathlib.Path(self.output_directory, ".temp").as_posix())

    def run(self):
        """Execute the pipeline, possibly in parallel.
        """
        # Joblib prints progress to stdout if verbose > 50
        verbose = 51 if self.show_progress else 0

        subject_ids = self._get_loader_subject_ids()
        # Note that returning any SimpleITK object in process_one_subject is
        # not supported yet, since they cannot be pickled
        if os.path.exists(self.output_df_path) and not self.overwrite:
            print("Dataset already processed...")
            shutil.rmtree(pathlib.Path(self.output_directory, ".temp").as_posix())
        else:
            Parallel(n_jobs=self.n_jobs, verbose=verbose)(
                    delayed(self._process_wrapper)(subject_id) for subject_id in subject_ids)
            self.save_data()


if __name__ == "__main__":
    pipeline = AutoPipeline(input_directory="C:/Users/qukev/BHKLAB/datasetshort/manifest-1598890146597/NSCLC-Radiomics-Interobserver1",
                            output_directory="C:/Users/qukev/BHKLAB/autopipelineoutputshort",
                            modalities="CT,RTSTRUCT",
                            visualize=False,
                            overwrite=False)

    # pipeline = AutoPipeline(input_directory="C:/Users/qukev/BHKLAB/hnscc_testing/HNSCC",
    #                         output_directory="C:/Users/qukev/BHKLAB/hnscc_testing_output",
    #                         modalities="CT,RTSTRUCT",
    #                         visualize=False)

    print(f'starting Pipeline...')
    pipeline.run()


    print(f'finished Pipeline!')