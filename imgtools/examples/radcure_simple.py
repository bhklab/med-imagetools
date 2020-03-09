from argparse import ArgumentParser

from ..pipeline import Pipeline
from ..ops import Input, Resample, DrawStructureSet, WriteImage
from ..io import ImageDirectoryLoader, read_dicom_series, read_dicom_rtstruct


class RADCUREPipeline(Pipeline):
    """Example processing pipeline for the RADCURE dataset.

    This pipeline loads the CT images and structure sets, re-samples the images,
    and draws the GTV contour using the resampled image.
    """
    def __init__(self, root_directory="/cluster/projects/radiomics/RADCURE_images/", output_directory="./processed", spacing=(1., 1., 1.)):
        self.root_directory = root_directory
        self.image_input = Input(ImageDirectoryLoader(self.root_directory, index_by="parent", subdir_path="*/ImageSet_*", reader=read_dicom_series))
        self.structure_set_input = Input(ImageDirectoryLoader(self.root_directory, index_by="parent", subdir_path="*/structures", reader=read_dicom_rtstruct))
        self.binary_mask = DrawStructureSet(roi_names="GTV")
        self.resample = Resample(spacing=spacing)
        self.write_image = WriteImage()

    def process_one_case(self, key):
        image = self.image_input(key)
        structure_set = self.structure_set_input(key)
        image = self.resample(image)
        mask = self.binary_mask(structure_set, image)
        self.write_image(key, image)
        self.write_mask(key, mask)


if __name__ == "__main__":
    parser = ArgumentParser("Example RADCURE processing pipeline.")
    parser.add_argument("root_directory",
                        type=str,
                        help="Path to the root directory of RADCURE dataset.")
    parser.add_argument("output_directory",
                        type=str,
                        help="Path to the directory where the processed images will be saved.")
    parser.add_argument("--spacing",
                        nargs=3,
                        type=float,
                        default=(1., 1., 1.),
                        help="The resampled voxel spacing in  (x, y, z) directions.")
    args = parser.parse_args()
    pipeline = RADCUREPipeline(args.root_directory,
                               output_directory=args.output_directory,
                               spacing=args.spacing)
    pipeline.run(progress=True)
