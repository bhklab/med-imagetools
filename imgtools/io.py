import os
import glob
import re
from typing import Optional
from collections import namedtuple
from itertools import chain

import numpy as np
import pandas as pd
import SimpleITK as sitk
from pydicom import dcmread
from pydicom.misc import is_dicom

from .image import physical_point_to_index
from .segmentation import StructureSet
from .utils.imageutils import image_to_array


def read_image(path):
    return sitk.ReadImage(path)


def read_numpy_array(path):
    return np.load(path)


def read_dicom_series(path: str,
                      recursive: bool = False,
                      series_id: Optional[str] = None) -> sitk.Image:
    """Read DICOM series as SimpleITK Image.

    Parameters
    ----------
    path
       Path to directory containing the DICOM series.

    recursive, optional
       Whether to recursively parse the input directory when searching for
       DICOM series,

    series_id, optional
       Specifies the DICOM series to load if multiple series are present in
       the directory. If None and multiple series are present, loads the first
       series found.


    Returns
    -------
    The loaded image.

    """
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(path,
                                                seriesID=series_id if series_id else "",
                                                recursive=recursive)
    reader.SetFileNames(dicom_names)
    return reader.Execute()


def read_dicom_rtstruct(path):
    return StructureSet.from_dicom_rtstruct(path)


def find_dicom_paths(root_path: str, yield_directories: bool = False) -> str:
    """Find DICOM file paths in the specified root directory file tree.

    Parameters
    ----------
    root_path
        Path to the root directory specifying the file hierarchy.

    yield_directories, optional
        Whether to yield paths to directories containing DICOM files
        or separately to each file (default).


    Yields
    ------
    The paths to DICOM files or DICOM-containing directories (if
    `yield_directories` is True).

    """
    # TODO add some filtering options
    for root, dirs, files in os.walk(root_path):
        if yield_directories:
            if any((is_dicom(os.path.join(root, f)) for f in files)):
                yield root
        else:
            for f in files:
                fpath = os.path.join(root, f)
                if is_dicom(fpath):
                    yield fpath

class BaseLoader:
    def __getitem__(self, key):
        raise NotImplementedError

    def __len__(self):
        return len(self.keys())

    def keys(self):
        raise NotImplementedError

    def items(self):
        raise NotImplementedError

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

class ImageCSVLoader(BaseLoader):
    def __init__(self,
                 csv_path,
                 colnames=[],
                 index_col=None,
                 readers=[read_image]):

        self.csv_path = csv_path
        self.colnames = colnames
        self.readers = readers

        if index_col is not None:
            colnames.append(index_col)

        self.paths = pd.read_csv(csv_path, usecols=colnames, index_col=index_col)

        if not isinstance(readers, list):
            readers = [readers] * len(colnames)

        self.output_tuple = namedtuple("Output", self.colnames)

    def __getitem__(self, key):
        row = self.paths.loc[key]
        outputs = {col: self.readers[i](row[col]) for i, col in enumerate(self.colnames)}
        return self.output_tuple(**outputs)

    def keys(self):
        return self.paths.keys()

    def items(self):
        return ((k, self[k]) for k in self.keys())


class ImageDirectoryLoader(BaseLoader):
    def __init__(self,
                 root_directory,
                 index_by="filename",
                 subdir_path=None,
                 exclude_paths=[],
                 reader=read_image):

        self.root_directory = root_directory
        self.index_by = index_by
        self.subdir_path = subdir_path
        self.exclude_paths = []
        for path in exclude_paths:
            if not path.startswith(self.root_directory):
                full_paths = glob.glob(os.path.join(root_directory, path))
                self.exclude_paths.extend(full_paths)
            else:
                full_path = path
                self.exclude_paths.append(full_path)
        self.reader = reader

        self.paths = self._generate_paths()

    def _generate_paths(self):
        paths = {}
        for f in os.scandir(self.root_directory):
            path = f.path
            if path in self.exclude_paths:
                continue
            if self.subdir_path:
                path = os.path.join(path, self.subdir_path)
            path = glob.glob(path)[0]
            key = self._extract_key_from_path(path)
            paths[key] = path
        return paths

    def _extract_key_from_path(self, path):
        filename, _ = os.path.splitext(os.path.basename(path))
        dirname = os.path.basename(os.path.dirname(path))
        if isinstance(self.index_by, str):
            if self.index_by == "filename":
                key = filename
            elif self.index_by == "parent":
                key = dirname
            else:
                key = re.search(self.index_by, path)[0]
        else:
            return self.index_by(path, filename, dirname)
        return key

    def __getitem__(self, key):
        path = self.paths[key]
        return self.reader(path)

    def keys(self):
        return self.paths.keys()

    def items(self):
        return ((k, self[k]) for k in self.keys())


class CombinedLoader(BaseLoader):
    def __init__(self, **kwargs):
        self.loaders = kwargs
        self.output_tuple = namedtuple("Output", list(self.loaders.keys()))

    def __getitem__(self, key):
        outputs = {name: loader[key] for name, loader in self.loaders.items()}
        return self.output_tuple(**outputs)

    def keys(self):
        return set(chain.from_iterable(loader.keys() for loader in self.loaders))

    def items(self):
        return ((k, self[k]) for k in self.keys())


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
