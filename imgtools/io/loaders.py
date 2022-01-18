import os, pathlib
import glob
import re
from typing import Optional, List
from collections import namedtuple
import json

import pandas as pd
import SimpleITK as sitk
import nrrd
from pydicom import dcmread

from joblib import Parallel, delayed
from tqdm.auto import tqdm

from ..modules import StructureSet
from ..modules import Dose
from ..modules import PET
from ..utils.crawl import *



def read_image(path):
    return sitk.ReadImage(path)

def read_header(path):
    return nrrd.read_header(path)

def read_dicom_series(path: str,
                      series_id: Optional[str] = None,
                      recursive: bool = False) -> sitk.Image:
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
    
    # Configure the reader to load all of the DICOM tags (public+private):
    # By default tags are not loaded (saves time).
    # By default if tags are loaded, the private tags are not loaded.
    # We explicitly configure the reader to load tags, including the
    # private ones.
    reader.MetaDataDictionaryArrayUpdateOn()
    reader.LoadPrivateTagsOn()

    return reader.Execute()


def read_dicom_rtstruct(path):
    return StructureSet.from_dicom_rtstruct(path)

def read_dicom_rtdose(path):
    return Dose.from_dicom_rtdose(path)

def read_dicom_pet(path,series=None):
    return PET.from_dicom_pet(path,series, "SUV")

def read_dicom_auto(path, series=None):
    if path is None:
        return None
    dcms = glob.glob(os.path.join(path, "*.dcm"))
    meta = dcmread(dcms[0])
    modality = meta.Modality
    if modality == 'CT' or modality == 'MR':
        return read_dicom_series(path,series)
    elif modality == 'PT':
        return read_dicom_pet(path,series)
    # elif len(dcms) == 1:
    #     meta = dcmread(dcms[0])
    #     modality = meta.Modality
    elif modality == 'RTSTRUCT':
        return read_dicom_rtstruct(dcms[0])
    elif modality == 'RTDOSE':
        return read_dicom_rtdose(path)
    else:
        if len(dcms)==1:
            raise NotImplementedError
        else:
            print("There were no dicoms in this path.")
            return None

def read_segmentation(path):
    # TODO read seg.nrrd
    pass

class BaseLoader:
    def __getitem__(self, subject_id):
        raise NotImplementedError

    def __len__(self):
        return len(self.keys())

    def keys(self):
        raise NotImplementedError

    def items(self):
        return ((k, self[k]) for k in self.keys())

    def values(self):
        return (self[k] for k in self.keys())

    def get(self, subject_id, default=None):
        try:
            return self[subject_id]
        except KeyError:
            return default

class ImageCSVLoader(BaseLoader):
    def __init__(self,
                 csv_path_or_dataframe,
                 colnames=[],
                 seriesnames=[],
                 id_column=None,
                 expand_paths=False,
                 readers=[read_image]):

        self.expand_paths = expand_paths
        self.readers = readers

        self.colnames = colnames
        self.seriesnames = seriesnames

        if isinstance(csv_path_or_dataframe, str):
            if id_column is not None and id_column not in colnames:
                colnames.append(id_column)
            self.paths = pd.read_csv(csv_path_or_dataframe,
                                     index_col=id_column)
        elif isinstance(csv_path_or_dataframe, pd.DataFrame):
            self.paths = csv_path_or_dataframe
            if id_column:
                self.paths = self.paths.set_index(id_column)
            if not self.colnames:
                self.colnames = self.paths.columns
        else:
            raise ValueError(f"Expected a path to csv file or pd.DataFrame, not {type(csv_path_or_dataframe)}.")

        if not isinstance(readers, list):
            readers = [readers] * len(self.colnames)

        self.output_tuple = namedtuple("Output", self.colnames)

    def __getitem__(self, subject_id):
        row = self.paths.loc[subject_id]
        paths = {col: row[col] for col in self.colnames}
        series = {col: row[col] for col in self.seriesnames}
        if self.expand_paths:
            # paths = {col: glob.glob(path)[0] for col, path in paths.items()}
            paths = {col: glob.glob(path)[0] if pd.notna(path) else None for col, path in paths.items()}
        outputs = {col: self.readers[i](path,series["series_"+("_").join(col.split("_")[1:])]) for i, (col, path) in enumerate(paths.items())}
        return self.output_tuple(**outputs)

    def keys(self):
        return list(self.paths.index)

    def items(self):
        return ((k, self[k]) for k in self.keys())


class ImageFileLoader(BaseLoader):
    def __init__(self,
                 root_directory,
                 get_subject_id_from="filename",
                 subdir_path=None,
                 exclude_paths=[],
                 reader=read_image):

        self.root_directory = root_directory
        self.get_subject_id_from = get_subject_id_from
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
            if f.path in self.exclude_paths:
                continue
            subject_dir_path = f.path
            if self.subdir_path:
                full_path = os.path.join(subject_dir_path, self.subdir_path)
            else:
                full_path = subject_dir_path
            try:
                full_path = glob.glob(full_path)[0]
            except IndexError:
                continue
            if os.path.isdir(full_path):
                full_path = os.path.join(full_path, "")
            subject_dir_name = os.path.basename(os.path.normpath(subject_dir_path))
            subject_id = self._extract_subject_id_from_path(full_path, subject_dir_name)
            paths[subject_id] = full_path
        return paths

    def _extract_subject_id_from_path(self, full_path, subject_dir_name):
        filename, _ = os.path.splitext(os.path.basename(full_path))
        if isinstance(self.get_subject_id_from, str):
            if self.get_subject_id_from == "filename":
                subject_id = filename
            elif self.get_subject_id_from == "subject_directory":
                subject_id = subject_dir_name
            else:
                subject_id = re.search(self.get_subject_id_from, full_path)[0]
        else:
            return self.get_subject_id_from(full_path, filename, subject_dir_name)
        return subject_id

    def __getitem__(self, subject_id):
        path = self.paths[subject_id]
        return self.reader(path)

    def keys(self):
        return self.paths.keys()



# class CombinedLoader(BaseLoader):
#     def __init__(self, **kwargs):
#         self.loaders = kwargs
#         self.output_tuple = namedtuple("Output", list(self.loaders.keys()))

#     def __getitem__(self, subject_id):
#         outputs = {name: loader[subject_id] for name, loader in self.loaders.items()}
#         return self.output_tuple(**outputs)

#     def keys(self):
#         return set(chain.from_iterable(loader.keys() for loader in self.loaders))

#     def items(self):
#         return ((k, self[k]) for k in self.keys())
