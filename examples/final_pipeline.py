import os
import glob
from numpy import mod
import pandas as pd

from argparse import ArgumentParser

from imgtools.io import read_dicom_auto
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
                 output_directory,
                 modalities,
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
        self.input_directory = "/cluster/projects/radiomics/PublicDatasets/HeadNeck/TCIA Head-Neck-PET-CT/Head-Neck-PET-CT"
        self.output_directory = output_directory
        self.spacing = spacing
        self.existing = [None] #self.existing_patients()

        #input operations
        self.input = ImageAutoInput(self.input_directory,modalities,n_jobs)

        # image processing ops
        self.resample = Resample(spacing=self.spacing)
        self.make_binary_mask = StructureSetToSegmentation(roi_names=[], continuous=False)

        # output ops
        self.output = ImageAutoOutput(self.output_directory,self.input.output_streams)

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
        counter = [0 for i in range(len(self.column_names))]
        for i,colnames in enumerate(self.column_names):
            #Based on the modality the operations will differ
            modality = colnames.split("_")[1]
            #If there are multiple connections existing, multiple connections means two modalities connected to one modality. They end with _1
            mult_conn = colnames.split("_")[-1]
            if read_results[i] is None:
                print("The subject id: {} has no {}".format(subject_id,("_").join(colnames.split("_")[1:])))
                pass
            elif modality=="CT":
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
                self.output(subject_id, image,modality)
                print(subject_id, " SAVED IMAGE")
            elif modality=="RTDOSE":
                try:
                    doses = read_results[i].resample_rt(image)
                except:
                    Warning("No CT image present. Returning dose image without resampling")
                    doses = read_results[i]
                    
                if mult_conn!="1":
                    self.output(subject_id, doses,modality)
                else:
                    counter[i] = counter[i]+1
                    self.output(subject_id+"_{}".format(counter[i]),doses,modality)
                print(subject_id, " SAVED DOSE")
            elif modality=="RTSTRUCT":
                structure_set = read_results[i]
                mask = self.make_binary_mask(structure_set, image)
                if mult_conn!="1":
                    self.output(subject_id, mask,modality)
                else:
                    counter[i] = counter[i]+1
                    self.output(subject_id+"_{}".format(counter[i]),mask,modality)
                print("SAVED MASK")
            elif modality=="PT":
                try:
                    pet = read_results[i].resample_pet(image)
                except:
                    Warning("No CT image present. Returning PET image without resampling")
                    pet = read_results[i]

                if mult_conn!="1":
                    self.output(subject_id, pet,modality)
                else:
                    counter[i] = counter[i]+1
                    self.output(subject_id+"_{}".format(counter[i]),pet,modality)
                print(subject_id, " SAVED PET")

        print("SUCCESS")
        return

if __name__ == "__main__":
    print("WASSUP")
    parser = ArgumentParser("Head-Neck-PET-CT processing pipeline.")
    parser.add_argument(
        "output_directory",
        type=str,
        help="Path to the directory where the processed images will be saved.")
    parser.add_argument(
        "--modalities",
        type=str,
        default="CT,RTDOSE,RTSTRUCT,PT",
        help="Query to get the sub-dataset. Type it like a string for ex: RTSTRUCT,CT,RTDOSE")
    parser.add_argument(
        "--spacing",
        nargs=3,
        type=float,
        default=(1., 1., 0.),
        help="The resampled voxel spacing in  (x, y, z) directions.")
    parser.add_argument(
        "--n_jobs",
        type=int,
        default=-1,
        help="The number of parallel processes to use.")
    parser.add_argument(
        "--show_progress",
        action="store_true",
        help="Whether to print progress to standard output.")
    args = parser.parse_args()
    pipeline = AutoPipeline(
        output_directory=args.output_directory,
        modalities=args.modalities,
        spacing=args.spacing,
        n_jobs=args.n_jobs,
        show_progress=args.show_progress)

    print(f'starting Pipeline...')
    # == Parallel Processing == 
    pipeline.run()
    
    # == Series (Single-core) Processing ==
    # Good for finding edge cases
    # subject_ids = pipeline._get_loader_subject_ids()
    # subject_ids = [202, 205, 209, 163, 149, 
    #                147, 146, 145, 144, 143, 
    #                140, 139, 138, 132, 130,
    #                129, 0, 1, 2, 3, 4, 5]
    # print('starting for loop...')
    # for subject_id in subject_ids:
    #     pipeline.process_one_subject(subject_id)

    # == Just Uno ==
    # Good for quickly checking on one sample. 
    # pipeline.process_one_subject(5) 
    print(f'finished Pipeline!')