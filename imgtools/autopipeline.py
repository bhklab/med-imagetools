import os

from argparse import ArgumentParser

from imgtools.ops import StructureSetToSegmentation, ImageAutoInput, ImageAutoOutput, Resample
from imgtools.pipeline import Pipeline

import SimpleITK as sitk
import pandas as pd
import warnings
from joblib import Parallel, delayed
import glob
import ast
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
                 missing_strategy="drop",
                 show_progress=False,
                 warn_on_error=False):

        super().__init__(
            n_jobs=n_jobs,
            missing_strategy=missing_strategy,
            show_progress=show_progress,
            warn_on_error=warn_on_error)

        # pipeline configuration
        self.input_directory = input_directory
        self.output_directory = output_directory
        self.spacing = spacing
        self.existing = [None] #self.existing_patients()

        #input operations
        self.input = ImageAutoInput(input_directory, modalities, n_jobs)
        
        self.output_df_path = os.path.join(self.output_directory, "dataset.csv")
        #Output component table
        if os.path.exists(self.output_df_path):
            self.output_df = pd.read_csv(self.output_df_path)
        else:
            self.output_df = self.input.df_combined
        #Name of the important columns which needs to be saved    
        self.output_streams = self.input.output_streams
        
        # image processing ops
        self.resample = Resample(spacing=self.spacing)
        self.make_binary_mask = StructureSetToSegmentation(roi_names=[], continuous=False)

        # output ops
        self.output = ImageAutoOutput(self.output_directory, self.output_streams)
        

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

        print("Processing:", subject_id)

        read_results = self.input(subject_id)
        print(read_results)

        print(subject_id, " start")
        #For counting multiple connections per modality
        counter = {"CT":0,"RTDOSE":0,"RTSTRUCT":0,"PT":0}
        
        metadata = {}
        for i, colname in enumerate(self.output_streams):
            modality = colname.split("_")[0]

            #Taking modality pairs if it exists till _1
            output_stream = ("_").join([item for item in colname.split("_") if item != "1"])

            #If there are multiple connections existing, multiple connections means two modalities connected to one modality. They end with _1
            mult_conn = colname.split("_")[-1] == "1"
            print(output_stream)

            if read_results[i] is None:
                print("The subject id: {} has no {}".format(subject_id, ("_").join(colname.split("_")[1:])))
                pass
            elif modality == "CT":
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
                    counter[modality] = counter[modality]+1
                    self.output(f"{subject_id}_{counter[modality]}", doses, output_stream)
                metadata[f"size_{output_stream}"] = str(doses.GetSize())
                metadata[f"metadata_{output_stream}"] = str(read_results[i].get_metadata())
                print(subject_id, " SAVED DOSE")
            elif modality == "RTSTRUCT":
                #For RTSTRUCT, you need image or PT
                structure_set = read_results[i]
                conn_to = output_stream.split("_")[-1]

                # make_binary_mask relative to ct/pet
                if conn_to == "CT":
                    mask = self.make_binary_mask(structure_set, image)
                elif conn_to == "PT":
                    mask = self.make_binary_mask(structure_set, pet)
                else:
                    raise ValueError("You need to pass a reference CT or PT/PET image to map contours to.")
                
                # save output
                if not mult_conn:
                    self.output(subject_id, mask, output_stream)
                else:
                    counter[modality] = counter[modality] + 1
                    self.output(f"{subject_id}_{counter[modality]}", mask, output_stream)
                metadata[f"roi_names_{output_stream}"] = str(structure_set.roi_names)

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
                    counter[modality] = counter[modality] + 1
                    self.output(f"{subject_id}_{counter[modality]}", pet, output_stream)
                metadata[f"size_{output_stream}"] = str(pet.GetSize())
                metadata[f"metadata_{output_stream}"] = str(read_results[i].get_metadata())
                print(subject_id, " SAVED PET")
        #Saving all the metadata in multiple text files
        with open(os.path.join(self.output_directory,f'temp_{subject_id}.txt'),'w') as f:
            f.write(str(metadata))
        return {subject_id: metadata}
    
    def save_data(self):
        files = glob.glob(os.path.join(self.output_directory,"*.txt"))
        for file in files:
            subject_id = file.replace("/","_").replace(".","_").split("_")[-2]
            A = file.open(files,"r").readlines()
            metadata = ast.literal_eval(A[0])
            self.output_df.loc[subject_id, list(metadata.keys())] = list(metadata.values())
        self.output_df.to_csv(self.output_df_path,mode="a",header=False)

    def _process_wrapper(self, subject_id):
        try:
            output = self.process_one_subject(subject_id)
            return output
        except Exception as e:
            message = f"{type(e).__name__} while processing subject {subject_id}: " + str(e)
            if self.warn_on_error:
                warnings.warn(message, category=RuntimeWarning)
            else:
                raise RuntimeError(message) from e

    def run(self):
        """Execute the pipeline, possibly in parallel.
        """
        # Joblib prints progress to stdout if verbose > 50
        verbose = 51 if self.show_progress else 0

        subject_ids = self._get_loader_subject_ids()
        # Note that returning any SimpleITK object in process_one_subject is
        # not supported yet, since they cannot be pickled
        try:
            outputs = Parallel(n_jobs=self.n_jobs, verbose=verbose)(
                delayed(self._process_wrapper)(subject_id) for subject_id in subject_ids)
            self.save_data()
        except Exception as e:
            self.save_data()
            raise RuntimeError(str(e))
        # self.save_data(outputs)
        

if __name__ == "__main__":
    parser = ArgumentParser("imgtools Automatic Processing Pipeline.")

    #arguments
    parser.add_argument("input_directory", type=str,
                        help="Path to top-level directory of dataset.")

    parser.add_argument("output_directory", type=str,
                        help="Path to output directory to save processed images.")

    parser.add_argument("--modalities", type=str, default="CT",
                        help="List of desired modalities. Type as string for ex: RTSTRUCT,CT,RTDOSE")

    parser.add_argument("--spacing", nargs=3, type=float, default=(1., 1., 0.),
                        help="The resampled voxel spacing in  (x, y, z) directions.")

    parser.add_argument("--n_jobs", type=int, default=-1,
                        help="The number of parallel processes to use.")

    parser.add_argument("--show_progress", action="store_true",
                        help="Whether to print progress to standard output.")

    args = parser.parse_args()
    pipeline = AutoPipeline(args.input_directory,
                            args.output_directory,
                            modalities=args.modalities,
                            spacing=args.spacing,
                            n_jobs=args.n_jobs,
                            show_progress=args.show_progress)

    print(f'starting Pipeline...')
    pipeline.run()


    print(f'finished Pipeline!')