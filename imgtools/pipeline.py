from collections import OrderedDict
from joblib import Parallel, delayed
from functools import reduce
from operator import or_
from .ops import Input


class Pipeline:
    """Base class for image processing pipelines.

    A pipeline can be created by subclassing, instantiating the required
    data loaders and operations from `ops` in the constructor and implementing
    the `process_one_case` method, which defines the processing steps for one
    case (i.e. one key from data loaders).
    """
    def __init__(self, n_jobs=0):
        """Initialize the base class.

        Parameters
        ----------
        n_jobs : int, optional
            The number of worker processes to use for parallel computation
            (default 0).
        """
        self.n_jobs = n_jobs
        self._keys = self._get_loader_keys()

    def _get_loader_keys(self):
        loaders = (v for v in self.__dict__.values() if isinstance(v, Input))
        try:
            return reduce(or_ (loader.keys() for loader in loaders))
        except TypeError:
            raise AttributeError("Pipeline must define at least one `Input` op.")

    def process_one_case(self, key, **kwargs):
        """Define the processing steps for one case.

        Parameters
        ----------
        key : str
            The key to be processed.
        """
        raise NotImplementedError

    def run(self, progress=False):
        """Execute the pipeline, possibly in parallel.

        Parameters
        ----------
        progress : bool, optional
            Whether to display the execution progress (default False).
        """
        verbose = 51 if progress else 0
        Parallel(n_jobs=self.n_jobs, verbose=verbose)(
            delayed(self.process_one_case)(key) for key in self._keys)


