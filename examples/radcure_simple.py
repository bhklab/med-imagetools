import os
from argparse import ArgumentParser

from imgtools.io import (ImageFileLoader, ImageFileWriter,
                         read_dicom_rtstruct, read_dicom_series)
from imgtools.ops import StructureSetToSegmentation, Input, Output, Resample
from imgtools.pipeline import Pipeline


###############################################################
# Example usage:
# python radcure_simple.py ./data/RADCURE/data ./RADCURE_output
###############################################################


class RADCUREPipeline(Pipeline):
    """Example processing pipeline for the RADCURE dataset.

    This pipeline loads the CT images and structure sets, re-samples the images,
    and draws the GTV contour using the resampled image.
    """

    def __init__(self,
                 input_directory,
                 output_directory,
                 spacing=(1., 1., 0.),
                 n_jobs=-1,
                 missing_strategy="drop",
                 show_progress=False):
        super().__init__(
            n_jobs=n_jobs,
            missing_strategy=missing_strategy,
            show_progress=show_progress)

        # pipeline configuration
        self.input_directory = input_directory
        self.output_directory = output_directory
        self.spacing = spacing

        # pipeline ops
        # input ops
        self.image_input = Input(
            ImageFileLoader(
                self.input_directory,                    # where to look for the images
                get_subject_id_from="subject_directory", # how to extract the subject ID, 'subject_directory' means use the name of the subject directory
                subdir_path="*/ImageSet_*",              # whether the images are stored in a subdirectory of the subject directory (also accepts glob patterns)
                reader=read_dicom_series                 # the function used to read individual images
            ))
        self.structure_set_input = Input(
            ImageFileLoader(
                self.input_directory,
                get_subject_id_from="subject_directory",
                subdir_path="*/structures/RTSTRUCT.dcm",
                reader=read_dicom_rtstruct))

        # image processing ops
        self.resample = Resample(spacing=self.spacing)
        # Note: the ROI name is temporarily changed to match the example data
        # since RADCURE is still not public. The correct ROI name for RADCURE is 'GTV'.
        self.make_binary_mask = StructureSetToSegmentation(roi_names="GTV-1")#"GTV")

        # output ops
        self.image_output = Output(
            ImageFileWriter(
                os.path.join(self.output_directory, "images"), # where to save the processed images
                filename_format="{subject_id}_image.nrrd",     # the filename template, {subject_id} will be replaced by each subject's ID at runtime
                create_dirs=True                               # whether to create directories that don't exists already
            ))
        self.mask_output = Output(
            ImageFileWriter(
                os.path.join(self.output_directory, "masks"),
                filename_format="{subject_id}_mask.nrrd",
                create_dirs=True))

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
           The ID of currently processed subject
        """

        image = self.image_input(subject_id)
        structure_set = self.structure_set_input(subject_id)
        image = self.resample(image)
        # note that the binary mask can be generated with correct spacing using
        # the resampled image, eliminating the need to resample it separately
        mask = self.make_binary_mask(structure_set, image)
        self.image_output(subject_id, image)
        self.mask_output(subject_id, mask)


if __name__ == "__main__":
    parser = ArgumentParser("Example RADCURE processing pipeline.")
    parser.add_argument(
        "input_directory",
        type=str,
        help="Path to the input directory of RADCURE dataset.")
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
        default=1,
        help="The number of parallel processes to use.")
    parser.add_argument(
        "--show_progress",
        action="store_true",
        help="Whether to print progress to standard output.")
    args = parser.parse_args()
    pipeline = RADCUREPipeline(
        input_directory=args.input_directory,
        output_directory=args.output_directory,
        spacing=args.spacing,
        n_jobs=args.n_jobs,
        show_progress=args.show_progress)
    pipeline.run()
