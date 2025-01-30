import os
import pathlib
import shutil
import warnings
from multiprocessing import cpu_count

import numpy as np
import pytest
import SimpleITK as sitk

from imgtools.io import ImageFileLoader, ImageFileWriter
from imgtools.ops import (
    BaseInput as Input,
    BaseOutput as Output,
)
from imgtools.pipeline import Pipeline


@pytest.fixture
def sample_input_output(tmp_path):
    input_paths = []
    output_paths = []
    for i in range(2):
        input_path = tmp_path / f'input_{i}'
        output_path = tmp_path / f'output_{i}'
        input_path.mkdir(exist_ok=True)
        output_path.mkdir(exist_ok=True)
        input_paths.append(input_path)
        output_paths.append(output_path)

        # generate some test data
        test_inputs = [sitk.GetImageFromArray(np.random.random((10, 10, 2))) for _ in range(4)]
        for j, img in enumerate(test_inputs):
            path = input_path / f'test{j}.nrrd'
            sitk.WriteImage(img, str(path))

    yield input_paths, output_paths
    # clean up
    shutil.rmtree(tmp_path)


class SimplePipelineTest(Pipeline):
    def __init__(self, input_path, output_path, n_jobs) -> None:
        super().__init__(n_jobs=n_jobs, show_progress=False)
        self.input_path = input_path
        self.output_path = output_path
        self.image_input = Input(ImageFileLoader(self.input_path))
        self.image_output = Output(ImageFileWriter(self.output_path))

    def process_one_subject(self, subject_id) -> None:
        image = self.image_input(subject_id)
        self.image_output(subject_id, image)


@pytest.mark.parametrize('n_jobs', [1, 2])
def test_output(n_jobs, sample_input_output) -> None:
    if cpu_count() < 2 and n_jobs == 2:
        n_jobs = 0
    input_paths, output_paths = sample_input_output
    pipeline = SimplePipelineTest(input_paths[0], output_paths[0], n_jobs)
    pipeline.run()

    input_dir, output_dir = input_paths[0], output_paths[0]

    for input_file, output_file in zip(
        sorted(os.listdir(input_dir)), sorted(os.listdir(output_dir))
    ):
        assert os.path.exists(pathlib.Path(output_dir, output_file))
        test_output = sitk.GetArrayFromImage(
            sitk.ReadImage(pathlib.Path(output_dir, output_file).as_posix())
        )
        true_output = sitk.GetArrayFromImage(
            sitk.ReadImage(pathlib.Path(input_dir, input_file).as_posix())
        )
        assert np.allclose(test_output, true_output)


class MultiInputPipelineTest(Pipeline):
    def __init__(
        self, input_path_0, input_path_1, output_path_0, output_path_1, n_jobs, missing_strategy
    ) -> None:
        super().__init__(n_jobs=n_jobs, missing_strategy=missing_strategy, show_progress=False)
        self.input_path_0 = input_path_0
        self.input_path_1 = input_path_1
        self.output_path_0 = output_path_0
        self.output_path_1 = output_path_1
        self.image_input_0 = Input(ImageFileLoader(self.input_path_0))
        self.image_input_1 = Input(ImageFileLoader(self.input_path_1))
        self.image_output_0 = Output(ImageFileWriter(self.output_path_0))
        self.image_output_1 = Output(ImageFileWriter(self.output_path_1))

    def process_one_subject(self, subject_id) -> None:
        image_0 = self.image_input_0(subject_id)
        image_1 = self.image_input_1(subject_id)
        if image_0 is not None:
            self.image_output_0(subject_id, image_0)
        if image_1 is not None:
            self.image_output_1(subject_id, image_1)


@pytest.mark.parametrize('n_jobs', [1, 2])
@pytest.mark.parametrize('missing_strategy', ['pass', 'drop'])
def test_missing_handling(n_jobs, missing_strategy, sample_input_output) -> None:
    if cpu_count() < 2 and n_jobs == 2:
        n_jobs = 0
    input_paths, output_paths = sample_input_output
    # simulate partial missing data
    os.remove(pathlib.Path(input_paths[0], 'test0.nrrd').as_posix())

    pipeline = MultiInputPipelineTest(
        input_paths[0], input_paths[1], output_paths[0], output_paths[1], n_jobs, missing_strategy
    )
    with warnings.catch_warnings(record=True) as w:
        pipeline.run()
        assert len(w) == 1
        assert missing_strategy in str(w[-1].message)

    if missing_strategy == 'drop':
        assert all(
            [
                not os.path.exists(pathlib.Path(output_paths[0], 'test0.nrrd').as_posix()),
                not os.path.exists(pathlib.Path(output_paths[1], 'test0.nrrd').as_posix()),
            ]
        )
    else:
        assert all(
            [
                not os.path.exists(pathlib.Path(output_paths[0], 'test0.nii.gz').as_posix()),
                os.path.exists(pathlib.Path(output_paths[1], 'test0.nii.gz').as_posix()),
            ]
        )
