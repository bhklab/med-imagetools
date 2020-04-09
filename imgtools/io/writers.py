import os
from datetime import datetime, timezone

import h5py
import numpy as np

import SimpleITK as sitk

from ..utils import image_to_array


class BaseWriter:
    def __init__(self, root_directory, filename_format, create_dirs=True):
        self.root_directory = root_directory
        self.filename_format = filename_format
        if create_dirs and not os.path.exists(self.root_directory):
            os.makedirs(self.root_directory)

    def put(self, *args, **kwargs):
        raise NotImplementedError

    def _get_path_from_subject_id(self, subject_id):
        now = datetime.now(timezone.utc)
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H%M%S")
        date_time = date + "_" + time
        out_filename = self.filename_format.format(subject_id=subject_id,
                                                   date=date,
                                                   time=time,
                                                   date_time=date_time)
        out_path = os.path.join(self.root_directory, out_filename)
        return out_path


class ImageFileWriter(BaseWriter):
    def __init__(self, root_directory, filename_format="{subject_id}.nrrd", create_dirs=True, compress=True):
        super().__init__(root_directory, filename_format, create_dirs)
        self.compress = compress

    def put(self, subject_id, image):
        # TODO (Michal) add support for .seg.nrrd files
        out_path = self._get_path_from_subject_id(subject_id)
        sitk.WriteImage(image, out_path, self.compress)


class NumpyWriter(BaseWriter):
    def __init__(self, root_directory, filename_format="{subject_id}.npy", create_dirs=True):
        super().__init__(root_directory, filename_format, create_dirs)
        self.root_directory = root_directory
        self.filename_format = filename_format

    def put(self, subject_id, image):
        out_path = self._get_path_from_subject_id(subject_id)
        if isinstance(image, sitk.Image):
            array, *_ = image_to_array(image) # TODO (Michal) optionally save the image geometry
        np.save(out_path, array)


class JSONMetadataWriter:
    # TODO (Michal)
    pass


class CSVMetadataWriter:
    # TODO (Michal)
    pass


# class MemoryWriter:
#     def __init__(self):
#         self.results = {}

#     def put(self, image, subject_id):
#         self.results[subject_id] = image

#     def __getitem__(self, subject_id):
#         return self.results[subject_id]

#     def get(self, subject_id, default=None):
#         try:
#             return self[subject_id]
#         except Subject_IdError:
#             return default

class HDF5Writer(BaseWriter):
    def __init__(self, root_directory, filename_format="{subject_id}.h5", create_dirs=True, save_geometry=True):
        super().__init__(root_directory, filename_format, create_dirs)
        self.save_geometry = save_geometry

    def put(self, subject_id, metadata=None, **kwargs):
        out_path = self._get_path_from_subject_id(subject_id)
        with h5py.File(out_path, "w") as f:
            for k, v in kwargs.items():
                array, origin, direction, spacing = image_to_array(v)
                dataset = f.create_dataset(k, data=array)
                dataset.attrs.create("subject_id", subject_id)
                if self.save_geometry:
                    dataset.attrs.create("origin", data=origin)
                    dataset.attrs.create("direction", data=direction)
                    dataset.attrs.create("spacing", data=spacing)
            if metadata:
                for k, attrs in metadata.items():
                    for name, v in attrs:
                        f[subject_id].attrs.create(name, data=v)


class MetadataWriter:
    pass
