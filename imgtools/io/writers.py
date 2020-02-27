import os

import numpy as np
import SimpleITK as sitk

from ..utils import image_to_array


class ImageFileWriter:
    def __init__(self, root_directory, output_format="nrrd", filename_format="{key}"):
        self.root_directory = root_directory
        self.output_format = output_format.lower()
        self.filename_format = filename_format
        self.writer = sitk.ImageFileWriter()

    def add(self, key, image):
        out_filename = self.filename_format.format(key=key) + "." + self.output_format
        out_path = os.path.join(self.root_directory, out_filename)
        self.writer.SetFileName(out_path)
        self.writer.Execute(image)


class NumpyWriter:
    def __init__(self, root_directory, filename_format="{key}.npy"):
        self.root_directory = root_directory
        self.filename_format = filename_format

    def add(self, key, image):
        filename = self.filename_format.format(key=key)
        path = os.path.join(self.root_directory, filename)
        if isinstance(image, sitk.Image):
            array, *_ = image_to_array(image) # TODO optionally save the image geometry
        np.save(path, array)


class MemoryWriter:
    def __init__(self):
        self.results = {}

    def add(self, image, key):
        self.results[key] = image

    def __getitem__(self, key):
        return self.results[key]

    def get(self, default=None):
        try:
            return self[key]
        except KeyError:
            return default

class HDF5Writer:
    def __init__(self, out_path, key):
        pass

    def add(self, key, image):
        pass

    def add_metadata(key, value):
        pass

class MetadataWriter:
    pass
