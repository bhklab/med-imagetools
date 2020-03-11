from collections import OrderedDict
from itertools import chain

from joblib import Parallel, delayed

from .ops import Input, BaseOp


class Pipeline:
    """Base class for image processing pipelines.

    A pipeline can be created by subclassing, instantiating the required
    data loaders and operations from `ops` in the constructor and implementing
    the `process_one_case` method, which defines the processing steps for one
    case (i.e. one key from data loaders).
    """
    def __init__(self, n_jobs=0, missing_strategy="drop", show_progress=True):
        """Initialize the base class.

        Parameters
        ----------
        n_jobs : int, optional
            The number of worker processes to use for parallel computation
            (default 0).
        """
        self.n_jobs = n_jobs
        self.missing_strategy = missing_strategy.lower()
        self.show_progress = show_progress
        if self.missing_strategy not in ["drop", "pass"]:
            raise ValueError(f"missing_strategy must be either of 'drop' or 'pass', got {missing_strategy}")
        self._keys = self._get_loader_keys()
        self._ops = self._get_all_ops()

    def _get_loader_keys(self):
        loaders = (v for v in self.__dict__.values() if isinstance(v, Input))
        all_keys = [loader.keys() for loader in loaders]
        unique_keys = set(chain.from_iterable(all_keys))

        if not all_keys:
            raise AttributeError("Pipeline must define at least one Input op")

        if self.missing_strategy == "drop":
            unique_keys = list(filter(lambda k: all((k in keys for keys in all_keys)), unique_keys))
        elif self.missing_strategy == "pass":
            unique_keys = list(unique_keys)
        return unique_keys

    def _get_all_ops(self):
        # TODO (Michal) return ops in actual order of execution
        return [v for v in self.__dict__.values() if isinstance(v, BaseOp)]

    def __repr__(self):
        attrs = [(k, v) for k, v in self.__dict__ if not isinstance(v, BaseOp) and not k.startswith("_")]
        args = ", ".join(f"{k}={v}" for k, v in attrs)
        return f"{self.__class__.__module__}.{self.__class__.__name__}({args})"

    def __str__(self):
        repr_ = self.__repr__()
        return repr_ + "\n" + "ops: " + ",\n".join(self._ops)


    def process_one_case(self, key):
        """Define the processing steps for one case.

        Parameters
        ----------
        key : str
            The key to be processed.
        """
        raise NotImplementedError

    def run(self):
        """Execute the pipeline, possibly in parallel.

        Parameters
        ----------
        progress : bool, optional
            Whether to display the execution progress (default False).
        """
        # Joblib prints progress to stdout if verbose > 50
        verbose = 51 if self.show_progress else 0

        # Note that result might be empty if the user's process_one_case
        # returns nothing.
        result = Parallel(n_jobs=self.n_jobs, verbose=verbose)(
            delayed(self.process_one_case)(key) for key in self._keys)
        return result


