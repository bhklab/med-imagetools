import os
from multiprocessing import cpu_count

import numpy as np
import SimpleITK as sitk

from pytest import mark

from imgtools.pipeline import Pipeline
from imgtools.ops import Input, Output
from imgtools.io import ImageDirectoryLoader, ImageFileWriter

TEST_INPUT_PATH = os.path.join("tests", "data", "images", "nrrd")

class PipelineTest(Pipeline):
    def __init__(self, n_jobs, output_path):
        super().__init__(n_jobs=n_jobs, show_progress=False)
        self.output_path = output_path
        self.image_input = Input(
            ImageDirectoryLoader(TEST_INPUT_PATH))
        self.image_output = Output(
            ImageFileWriter(self.output_path))

    def process_one_subject(self, subject_id):
        image = self.image_input(subject_id)
        self.image_output(subject_id, image)

@mark.parametrize("n_jobs", [1, 2])
def test_output(n_jobs, tmp_path):
    if cpu_count() < 2 and n_jobs == 2:
        n_jobs = 0
    output_path = tmp_path
    output_path.mkdir(exist_ok=True)
    pipeline = PipelineTest(n_jobs, output_path)
    pipeline.run()

    for f in os.scandir(TEST_INPUT_PATH):
        test_path = os.path.join(output_path, f.name)
        assert os.path.exists(test_path)
        test_output = sitk.GetArrayFromImage(sitk.ReadImage(test_path))
        true_output = sitk.GetArrayFromImage(sitk.ReadImage(f.path))
        assert np.allclose(test_output, true_output)

if __name__ == "__main__":
    test_output(0, "./output/test_output_0_0/")
