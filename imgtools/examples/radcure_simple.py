from argparse import ArgumentParser

from ..pipeline import Pipeline
from ..ops import Input, Resample, DrawStructureSet, WriteImage
from ..io import ImageDirectoryLoader, read_dicom_series, read_dicom_rtstruct


class RADCUREPipeline(Pipeline):
    """Example processing pipeline for the RADCURE dataset.

    This pipeline loads the CT images and structure sets, re-samples the images,
    and draws the GTV contour using the resampled image.
    """
    def __init__(self,
                 root_directory="/cluster/projects/radiomics/RADCURE_images/",
                 output_directory="./processed",
                 spacing=(1., 1., 1.),
                 n_jobs=2,
                 missing_strategy="drop",
                 show_progress=False):
        super(RADCUREPipeline, self).__init__(n_jobs=n_jobs,
                                              missing_strategy=missing_strategy,
                                              show_progress=show_progress)
        self.root_directory = root_directory
        self.image_input = Input(ImageDirectoryLoader(self.root_directory,
                                                      index_by="parent",
                                                      subdir_path="*/ImageSet_*",
                                                      reader=read_dicom_series))
        self.structure_set_input = Input(ImageDirectoryLoader(self.root_directory,
                                                              index_by="parent",
                                                              subdir_path="*/structures",
                                                              reader=read_dicom_rtstruct))
        self.binary_mask = DrawStructureSet(roi_names="GTV")
        self.resample = Resample(spacing=spacing)
        self.statistics = ImageStatistics()
        self.image_output = Output(ImageFileWriter())
        self.mask_output = Output(ImageFileWriter())

    def process_one_case(self, key):
        image = self.image_input(key)
        structure_set = self.structure_set_input(key)
        image = self.resample(image)
        mask = self.binary_mask(structure_set, image)
        self.image_output(key, image)
        self.mask_output(key, mask)


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
    parser.add_argument("--n_jobs",
                        type=int,
                        default=0,
                        help="The number of parallel processes to use".)
    parser.add_argument("--show_progress",
                        action="store_true"
                        help="Whether to print progress to standard output".)
    args = parser.parse_args()
    pipeline = RADCUREPipeline(args.root_directory,
                               output_directory=args.output_directory,
                               spacing=args.spacing,
                               n_jobs=args.n_jobs,
                               show_progress=args.show_progress)
    pipeline.run()
