import os
import glob
import pandas as pd

from argparse import ArgumentParser

from imgtools.io import read_dicom_rtstruct, read_dicom_series, read_dicom_auto
from imgtools.ops import StructureSetToSegmentation, ImageCSVInput, ImageFileOutput, Resample
from imgtools.pipeline import Pipeline

import SimpleITK as sitk

import warnings


###############################################################
# Example usage:
# python radcure_simple.py ./data/RADCURE/data ./RADCURE_output
###############################################################


class QCPipeline(Pipeline):
    """Example processing pipeline for the RADCURE dataset.
    This pipeline loads the CT images and structure sets, re-samples the images,
    and draws the GTV contour using the resampled image.
    """

    def __init__(self,
                 output_directory,
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
        self.output_directory = output_directory
        self.spacing = spacing
        self.existing = [None] #self.existing_patients()

        df = pd.read_csv("/cluster/projects/radiomics/PublicDatasets/HeadNeck/TCIA Head-Neck-PET-CT/imgtools_Head-Neck-PET-CT_2.csv", index_col=0)
        rt = df[df['modality'] == 'RTSTRUCT']
        pet = df[df['modality'] == 'PT']
        ct = df[df['modality'] == 'CT']

        rt_nPT = rt[~rt['study'].isin(pet['study'].unique())]
        ct_nPT = ct[~ct['study'].isin(pet['study'].unique())]

        self.df_combined = pd.merge(ct_nPT, rt_nPT, left_on='series', right_on='reference')

        def find_rt(s):
            return glob.glob(os.path.join(s, "*"))[0]

        # self.df_combined['folder_y'] = self.df_combined['folder_y'].apply(find_rt)

        # declare csv input
        self.input = ImageCSVInput(self.df_combined,
                                   ["folder_x", "folder_y"],    
                                   readers=[read_dicom_auto, read_dicom_auto])

        # image processing ops
        self.resample = Resample(spacing=self.spacing)
        self.make_binary_mask = StructureSetToSegmentation(roi_names=[], continuous=False)

        # output ops
        self.image_output = ImageFileOutput(
            os.path.join(self.output_directory, "images"), 
            filename_format="{subject_id}_image.nrrd",                         
        )
        self.mask_output = ImageFileOutput(
            os.path.join(self.output_directory, "masks"),
            filename_format="{subject_id}_mask.seg.nrrd",
        )

        self.existing_patients()
        print(self.existing)

    def existing_patients(self):
        existing_masks = os.listdir(os.path.join(self.output_directory, "masks"))
        self.existing = [i.split("_mask")[0] for i in existing_masks]

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
        if str(subject_id) in self.existing:
            return

        image, structure_set = self.input(subject_id)
        print(image, structure_set)
        print(image.GetSize(), len(structure_set.roi_names))
        if len(image.GetSize()) == 4:
            assert image.GetSize()[-1] == 1, f"There is more than one volume in this CT file for {subject_id}."
            extractor = sitk.ExtractImageFilter()
            extractor.SetSize([*image.GetSize()[:3], 0])
            extractor.SetIndex([0, 0, 0, 0])    
            
            image = extractor.Execute(image)
            print(image.GetSize())

        image = self.resample(image)
        # note that the binary mask can be generated with correct spacing using
        # the resampled image, eliminating the need to resample it separately
        
        # try:
        print(subject_id, " start")

        self.image_output(subject_id, image)
        print(subject_id, " SAVED IMAGE")
        
        mask = self.make_binary_mask(structure_set, image)
        self.mask_output(subject_id, mask)
        print(subject_id, " DONE MASK")
        print(subject_id, " SUCCESS")
        # except Exception as e:
        #     print(subject_id, e)
        
        return


if __name__ == "__main__":
    print("WASSUP")
    parser = ArgumentParser("Head-Neck-PET-CT processing pipeline.")
    parser.add_argument(
        "output_directory",
        type=str,
        help="Path to the directory where the processed images will be saved.")
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
    pipeline = QCPipeline(
        output_directory=args.output_directory,
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