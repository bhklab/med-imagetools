from collections import OrderedDict
from joblib import Parallel, delayed
from functools import reduce
from operator import or_


class Pipeline:
    def __init__(self, n_jobs):
        self.n_jobs = n_jobs
        self._keys = self._get_loader_keys()

    def _get_loader_keys(self):
        loaders = (v for v in self.__dict__.values() if isinstance(v, BaseLoader))
        try:
            return reduce(or_ (loader.keys() for loader in loaders))
        except TypeError:
            raise AttributeError("Pipeline must define at least one data source (subclass of io.BaseLoader).")

    def process_one_case(self, key, **kwargs):
        raise NotImplementedError

    def run(self):
        Parallel(n_jobs=self.n_jobs)(delayed(self.process_one_case)(key) for key in self._keys)


