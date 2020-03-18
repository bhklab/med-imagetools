import os
from multiprocessing import cpu_count

import numpy as np
import SimpleITK as sitk
from pytest import mark

from imgtools.io import ImageFileLoader, ImageFileWriter
from imgtools.ops import Input, Output
from imgtools.pipeline import Pipeline


class PipelineTest(Pipeline):
    def __init__(self, n_jobs, input_path, output_path):
        super().__init__(n_jobs=n_jobs, show_progress=False)
        self.input_path = input_path
        self.output_path = output_path
        self.image_input = Input(
            ImageFileLoader(self.input_path))
        self.image_output = Output(
            ImageFileWriter(self.output_path))

    def process_one_subject(self, subject_id):
        image = self.image_input(subject_id)
        self.image_output(subject_id, image)

@mark.parametrize("n_jobs", [1, 2])
def test_output(n_jobs, tmp_path):
    if cpu_count() < 2 and n_jobs == 2:
        n_jobs = 0
    input_path = tmp_path / "input"
    output_path = tmp_path / "output"
    input_path.mkdir(exist_ok=True)
    output_path.mkdir(exist_ok=True)

    # generate some test data
    test_inputs = [sitk.GetImageFromArray(np.random.random((10, 10, 2))) for _ in range(4)]
    for i, img in enumerate(test_inputs):
        path = input_path / f"test{i}.nrrd"
        sitk.WriteImage(img, str(path))

    pipeline = PipelineTest(n_jobs, input_path, output_path)
    pipeline.run()

    for i, img in enumerate(test_inputs):
        test_path = output_path / f"test{i}.nrrd"
        assert test_path.exists()
        test_output = sitk.GetArrayFromImage(sitk.ReadImage(str(test_path)))
        true_output = sitk.GetArrayFromImage(img)
        assert np.allclose(test_output, true_output)
