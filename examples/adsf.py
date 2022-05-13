import os
from argparse import ArgumentParser

from imgtools.io import (ImageFileLoader, ImageFileWriter,
                         read_dicom_rtstruct, read_dicom_series, read_dicom_rtdose, read_dicom_pet)
from imgtools.ops import StructureSetToSegmentation, ImageFileInput, ImageFileOutput, Resample
from imgtools.pipeline import Pipeline

class samplePipeline(Pipeline):
    def __init__(self,
                 input_directory,
                 output_directory,
                 spacing,
                 n_jobs):
        #i think that it was pretty clear from the sample notebook that we
        #need to inheret the Pipeline object as a parent for any pipeline we use
        #maybe we can make that even more clear in the docstring but it should
        #be fine as it is rn
        
        #what is the default n_jobs?
        super().__init__(n_jobs=n_jobs)
        
        self.input_directory = input_directory
        self.output_directory = output_directory
        self.spacing = spacing
        self.image_input = ImageFileInput(
            self.input_directory,                    # where to look for the images
            get_subject_id_from="subject_directory", # how to extract the subject ID, 'subject_directory' means use the name of the subject directory
            subdir_path="*/NA-*",
            # whether the images are stored in a subdirectory of the subject directory (also accepts glob patterns)
            reader=read_dicom_series                 # the function used to read individual images
        )
        self.structure_set_input = ImageFileInput(
            self.input_directory,
            get_subject_id_from="subject_directory",
            subdir_path="*/1.000000-ARIA RadOnc Structure Sets-*/1-1.dcm",
            reader=read_dicom_rtstruct
        )

        self.make_binary_mask = StructureSetToSegmentation(roi_names="GTV.*")#"GTV")
        self.image_output = ImageFileOutput(
            os.path.join(self.output_directory, "images"), # where to save the processed images
            filename_format="{subject_id}_image.nrrd",     # the filename template, {subject_id} will be replaced by each subject's ID at runtime
            create_dirs=True,                              # whether to create directories that don't exists already
            compress=True                                  # enable compression for NRRD format
        )
        self.mask_output = ImageFileOutput(
            os.path.join(self.output_directory, "masks"),
            filename_format="{subject_id}_mask.nrrd",
            create_dirs=True,
            compress=True
        )
    def process_one_subject(self, subject_id):
        image = self.image_input(subject_id)
        structure_set = self.structure_set_input(subject_id)
        # note that the binary mask can be generated with correct spacing using
        # the resampled image, eliminating the need to resample it separately

        print(structure_set.roi_names)
        mask = self.make_binary_mask(structure_set, image)
        self.image_output(subject_id, image)
        self.mask_output(subject_id, mask)

if __name__ == "__main__":
    pipeline = samplePipeline(
            input_directory="C:/Users/qukev/BHKLAB/dataset/manifest-1598890146597/NSCLC-Radiomics-Interobserver1",
            output_directory="C:/Users/qukev/BHKLAB/output",
            spacing=(1.,1.,0.),
            n_jobs=1)
    # pipeline.run()
    subject_ids = pipeline._get_loader_subject_ids()
    for subject_id in subject_ids:
        pipeline.process_one_subject(subject_id)