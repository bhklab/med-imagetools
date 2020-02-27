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


class MyPipeline(Pipeline):
    def __init__(self, image_root, mask_root, resample_mask=False, n_jobs=3):
        super(MyPipeline, self).__init__(n_jobs=n_jobs)
        self.image_loader = io.ImageLoader(image_root)
        self.mask_loader = io.MaskLoader(image_root)
        self.resample = Resample(spacing=(1., 1., 1.))
        self.image_writer = io.ImageWriter("./results")
        self.mask_writer = io.ImageWriter("./results")

    def process_one_case(self, key):
        image = self.image_loader.get(key)
        mask = self.mask_loader.get(key)
        image = self.resample(image)
        mask = self.resample(mask)
        self.image_writer.add(image, key)
        self.mask_writer.add(mask, key)

    def run(self):
        Parallel(n_jobs=self.n_jobs)(delayed(self.process_one_case)(key) for key in self._keys)
