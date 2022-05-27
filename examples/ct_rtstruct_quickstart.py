import pathlib

from argparse import ArgumentParser

from imgtools.io import read_dicom_rtstruct, read_dicom_series
from imgtools.ops import StructureSetToSegmentation, ImageFileInput, ImageFileOutput
from imgtools.pipeline import Pipeline


################################################################
#every pipeline needs to be inherited from the Pipeline class
class samplePipeline(Pipeline):
    """
    Sample starter pipeline for processing CT images and their relevant RTSTRUCTs

    This pipeline is designed to be used with the following directory structure:
    - input_directory
        - subject_directory (the subject's name)
            - CT_file_convention
                - CT_image_1.dcm
                - CT_image_2.dcm
                - ...
            - RTSTRUCT_file_convention
                - RTSTRUCT.dcm

    The pipeline will look for CT images in the CT_file_convention and RTSTRUCTs in the
    RTSTRUCT_file_convention. The pipeline will save the processed images and masks in
    the output_directory.

    Attributes:
        input_directory (str): the directory where the input images and RTSTRUCTs are stored
        output_directory (str): the directory where the output images and masks will be stored
        CT_file_convention (str): the glob-supported naming convention for the CT images
        RTSTRUCT_file_convention (str): the name of the directory where the RTSTRUCTs are stored

    Methods:
        process_one_subject(subject_id): how to process one subject (this function must be defined for all pipelines)
    """


    def __init__(self,
                 input_directory,
                 output_directory,
                 CT_file_convention,
                 RTSTRUCT_file_convention):
        super().__init__()
        
        self.input_directory = input_directory
        self.output_directory = output_directory

        # the file-reading input class for all the CT images
        self.image_input = ImageFileInput(
            self.input_directory,                    # where to look for the images
            get_subject_id_from="subject_directory", # how to extract the subject ID, 'subject_directory' means use the name of the subject directory. 'filename' means use the name of the file
            subdir_path=CT_file_convention,          # whether the images are stored in a subdirectory of the subject directory (also accepts glob patterns)
            reader=read_dicom_series                 # the function used to read individual images
        )

        # the file-reading input class for all the RTSTRUCTs
        self.structure_set_input = ImageFileInput(
            self.input_directory,
            get_subject_id_from="subject_directory",
            subdir_path=RTSTRUCT_file_convention,
            reader=read_dicom_rtstruct
        )

        # class for converting the RTSTRUCT DICOMs to binary masks
        self.make_binary_mask = StructureSetToSegmentation(roi_names=[])

        # the file-writing output class for all the processed images
        self.image_output = ImageFileOutput(
            pathlib.Path(self.output_directory, "images").as_posix(), # where to save the processed images
            filename_format="{subject_id}_image.nii.gz",              # the filename template, {subject_id} will be replaced by each subject's ID at runtime
            create_dirs=True                                          # whether to create directories that don't exists already
        )

        # the file-writing output class for all the processed masks
        self.mask_output = ImageFileOutput(
            pathlib.Path(self.output_directory, "masks").as_posix(),
            filename_format="{subject_id}_mask.nii.gz",
            create_dirs=True
        )



    # pipeline classes must have a definition for how to process one patient
        
    def process_one_subject(self, subject_id):
        # calling the classes initialized in __init__()
        image = self.image_input(subject_id)
        structure_set = self.structure_set_input(subject_id)

        # print all the regions of interest in the RTSTRUCT
        print(structure_set.roi_names)

        # convert the RTSTRUCT to a binary mask
        mask = self.make_binary_mask(structure_set, image)
        self.image_output(subject_id, image)
        self.mask_output(subject_id, mask)

if __name__ == "__main__":
    parser = ArgumentParser("Quickstart example")

    parser.add_argument("input_directory", type=str,
                        help="The directory containing the input data")
    parser.add_argument("output_directory", type=str,
                        help="The directory where the output will be stored")

    # look at your input directory and look at how all the DICOM files are named
    CT_file_convention = "*/NA-*"
    RTSTRUCT_file_convention = "*/1.000000-ARIA RadOnc Structure Sets-*/1-1.dcm"

    args = parser.parse_args()
    pipeline = samplePipeline(
        input_directory=args.input_directory,
        output_directory=args.output_directory,
        CT_file_convention=CT_file_convention,
        RTSTRUCT_file_convention=RTSTRUCT_file_convention
    )

    #process each patient one by one in a linear fashion
    subject_ids = pipeline._get_loader_subject_ids()
    for subject_id in subject_ids:
        pipeline.process_one_subject(subject_id)
    
    # pipeline.run()
    # alternatively, use pipeline.run() to run the pipeline in parallel using joblib, which is more efficient for larger datasets