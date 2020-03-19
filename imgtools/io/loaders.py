import os
import glob
import re
from typing import Optional
from collections import namedtuple
from itertools import chain

import pandas as pd

from .common import read_image


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
                 csv_path,
                 colnames=[],
                 id_column=None,
                 readers=[read_image]):

        self.csv_path = csv_path
        self.colnames = colnames
        self.readers = readers

        if id_column is not None:
            colnames.append(id_column)

        self.paths = pd.read_csv(csv_path, usecols=colnames, index_col=id_column)

        if not isinstance(readers, list):
            readers = [readers] * len(colnames)

        self.output_tuple = namedtuple("Output", self.colnames)

    def __getitem__(self, subject_id):
        row = self.paths.loc[subject_id]
        outputs = {col: self.readers[i](row[col]) for i, col in enumerate(self.colnames)}
        return self.output_tuple(**outputs)

    def keys(self):
        return self.paths.keys()

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
