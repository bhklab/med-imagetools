import copy
import pathlib

import h5py
import numpy as np
import pytest
import SimpleITK as sitk

from imgtools.ops.ops import (
    CentreCrop,
    ClipIntensity,
    Crop,
    HDF5Output,
    ImageStatistics,
    MinMaxScale,
    NumpyOutput,
    Resample,
    Resize,
    StandardScale,
    WindowIntensity,
    Zoom,
)


img_shape = (100, 100, 100)
direction = (1, 0, 0, 0, 1, 0, 0, 0, 1)
origin = (37, 37, 37)
spacing = (0.37, 0.37, 0.37)

# build blank image sample
blank = sitk.Image(img_shape, sitk.sitkInt16)  # np.zeros((100,100,100))
blank.SetDirection(direction)
blank.SetOrigin(origin)
blank.SetSpacing(spacing)


class TestOutput:
    @pytest.mark.parametrize('op', [NumpyOutput, HDF5Output])  # , "CT,RTDOSE,PT"])
    def test_output(self, op, tmp_path) -> None:

        output_path = tmp_path / 'temp_outputs'
        output_path.mkdir()
        # get class name
        class_name = op.__name__

        # save output
        saver = op(output_path, create_dirs=False)
        saver(class_name, blank)
        saved_path = pathlib.Path(
            output_path, saver.filename_format.format(subject_id=class_name)
        ).as_posix()

        # check output
        if class_name == 'HDF5Output':
            f = h5py.File(saved_path, 'r')
            img = f['image']
            assert tuple(img.attrs['origin']) == origin
            assert tuple(img.attrs['direction']) == direction
            assert tuple(img.attrs['spacing']) == spacing
        elif class_name == 'NumpyOutput':
            img = np.load(saved_path)

        # class-agnostic
        assert img.shape == img_shape


class TestTransform:
    @pytest.mark.parametrize(
        'op,params',
        [
            (Resample, {'spacing': 3.7}),
            (Resize, {'size': 10}),
            (Zoom, {'scale_factor': 0.1}),
            (Crop, {'crop_centre': (20, 20, 20), 'size': 10}),
            (CentreCrop, {'size': 10}),
        ],
    )
    def test_transform(self, op, params) -> None:
        transform = op(**params)
        new_img = transform(blank)

        # check output
        # resample
        if isinstance(transform, Resample):
            assert new_img.GetSpacing() == (3.7, 3.7, 3.7)

        # not zoom
        if not isinstance(transform, Zoom):
            assert new_img.GetSize() == (10, 10, 10)

        # zoom
        if isinstance(transform, Zoom):
            assert new_img.GetSize() == (100, 100, 100)
            assert new_img.GetSpacing() == (0.37, 0.37, 0.37)


class TestIntensity:
    @pytest.mark.parametrize(
        'op,params',
        [
            (ClipIntensity, {'lower': 0, 'upper': 500}),
            (WindowIntensity, {'window': 500, 'level': 250}),
            (StandardScale, {}),
            (MinMaxScale, {'minimum': 0, 'maximum': 1000}),
        ],
    )
    def test_intesity(self, op, params) -> None:
        img_cube = copy.deepcopy(blank)
        img_cube[5:15, 5:15, 5:15] = 1000

        intensify = op(**params)
        new_img = intensify(img_cube)
        stats = ImageStatistics()(new_img)

        # check output
        if isinstance(intensify, (ClipIntensity, WindowIntensity)):
            assert stats.sum == 5e5
        elif isinstance(intensify, StandardScale):
            assert np.allclose(stats.mean, 0.0)
            assert np.allclose(stats.standard_deviation, 1.0, rtol=1e-1)
