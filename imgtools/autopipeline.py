import os
import glob
from numpy import mod
import pandas as pd

from argparse import ArgumentParser

from imgtools.ops import StructureSetToSegmentation, ImageAutoInput, ImageAutoOutput, Resample
from imgtools.pipeline import Pipeline

import SimpleITK as sitk

import warnings


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

        #For the pipeline
        self.graph = self.input.df_combined.copy()
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
           The ID of currently processed subjectsqusqueue
        """

        print("Processing:", subject_id)

        read_results = self.input(subject_id)
        print(read_results)

        print(subject_id, " start")
        #For counting multiple connections per modality
        counter = [0 for _ in range(len(self.output_streams))]
        
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
                self.graph.loc[subject_id, f"size_{output_stream}"] = image.GetSize()
                print(subject_id, " SAVED IMAGE")
            elif modality == "RTDOSE":
                try: #For cases with no image present
                    doses = read_results[i].resample_rt(image)
                except:
                    Warning("No CT image present. Returning dose image without resampling")
                    doses = read_results[i]
                
                # save output
                if mult_conn:
                    self.output(subject_id, doses, output_stream)
                else:
                    counter[i] = counter[i]+1
                    self.output(f"{subject_id}_{counter[i]}", doses, output_stream)
                self.graph.loc[subject_id, f"size_{output_stream}"] = doses.GetSize()
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
                    raise ValueError("You need to pass CT images or PT images so that mask can be made")
                
                # save output
                if mult_conn:
                    self.output(subject_id, mask, output_stream)
                else:
                    counter[i] = counter[i] + 1
                    self.output(f"{subject_id}_{counter[i]}", mask, output_stream)
                self.graph.loc[subject_id, f"roi_names_{output_stream}"] = structure_set.roi_names

                print(subject_id, "SAVED MASK ON", conn_to)
            elif modality == "PT":
                try:
                    #For cases with no image present
                    pet = read_results[i].resample_pet(image)
                except:
                    Warning("No CT image present. Returning PET image without resampling")
                    pet = read_results[i]

                if mult_conn!="1":
                    self.output(subject_id, pet, output_stream)
                else:
                    counter[i] = counter[i] + 1
                    self.output(f"{subject_id}_{counter[i]}", pet, output_stream)
                self.graph.loc[subject_id, f"size_{output_stream}"] = pet.GetSize()
                print(subject_id, " SAVED PET")
        return

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
    if args.n_jobs > 1 or args.n_jobs == -1:     # == Parallel Processing == 
        pipeline.run()
        pipeline.graph.to_csv(os.path.join(args.output_directory, "dataset.csv"))
    elif args.n_jobs == 1:                       # == Series (Single-core) Processing ==
        subject_ids = pipeline._get_loader_subject_ids()
        for subject_id in subject_ids:
            pipeline.process_one_subject(subject_id)

    print(f'finished Pipeline!')