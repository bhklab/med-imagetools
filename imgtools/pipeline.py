import warnings
from itertools import chain

from joblib import Parallel, delayed

from .ops import BaseOp, BaseInput


class Pipeline:
    """Base class for image processing pipelines.

    A pipeline can be created by subclassing, instantiating the required
    data loaders and operations from `ops` in the constructor and implementing
    the `process_one_case` method, which defines the processing steps for one
    case (i.e. one subject_id from data loaders).
    """
    def __init__(self, n_jobs=1, missing_strategy="drop", show_progress=True):
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

    def _get_loader_subject_ids(self):
        loaders = (v.loader for v in self.__dict__.values() if isinstance(v, BaseInput))
        all_subject_ids = [loader.keys() for loader in loaders]
        unique_subject_ids = set(chain.from_iterable(all_subject_ids))

        if not all_subject_ids:
            raise AttributeError("Pipeline must define at least one input op (subclass of ops.BaseInput)")

        result = []
        for subject_id in unique_subject_ids:
            if not all((subject_id in subject_ids for subject_ids in all_subject_ids)):
                message = f"Subject {subject_id} is missing some of the input data "
                if self.missing_strategy == "drop":
                    message += f"and will be dropped accoring to current missing strategy ({self.missing_strategy})."
                elif self.missing_strategy == "pass":
                    message += f"but will be passed accoring to current missing strategy ({self.missing_strategy})."
                    result.append(subject_id)
                warnings.warn(message, category=RuntimeWarning)
                continue
            result.append(subject_id)

        return result

    def _get_all_ops(self):
        # TODO (Michal) return ops in actual order of execution
        return [v for v in self.__dict__.values() if isinstance(v, BaseOp)]

    def __repr__(self):
        attrs = [(k, v) for k, v in self.__dict__.items() if not isinstance(v, BaseOp) and not k.startswith("_")]
        args = ", ".join(f"{k}={v}" for k, v in attrs)
        return f"{self.__class__.__module__}.{self.__class__.__name__}({args})"

    def __str__(self):
        repr_ = self.__repr__()
        ops = self._get_all_ops()
        if not ops:
            ops = "<none>"
        else:
            ops = ",\n".join(ops)
        return repr_ + "\n" + "ops: (\n" + ops + "\n)"

    def process_one_subject(self, subject_id):
        """Define the processing steps for one case.

        Parameters
        ----------
        subject_id : str
            The ID of the subject to be processed.
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

        subject_ids = self._get_loader_subject_ids()
        # Note that returning any SimpleITK object in process_one_subject is
        # not supported, since they cannot be pickled
        Parallel(n_jobs=self.n_jobs, verbose=verbose)(
            delayed(self.process_one_subject)(subject_id) for subject_id in subject_ids)


class SequentialPipeline(Pipeline):
    def __init__(self, ops_list):
        self.source = ops_list.pop(0)
        self.sink = ops_list.pop() if isinstance(ops_list[-1], Output) else None
        self.ops_list = ops_list

    def process_one_subject(self, subject_id):
        image = self.source(subject_id)
        for op in self.ops_list:
            image = op(image)
        if self.sink is not None:
            self.sink(image)
        return image
