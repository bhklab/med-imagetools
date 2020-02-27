import os
import glob
import re
from typing import Optional
from collections import namedtuple
from itertools import chain

import pandas as pd

from .common import read_image


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
