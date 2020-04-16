import os
import json
import csv
import pickle
from datetime import datetime, timezone

import h5py
import numpy as np

import SimpleITK as sitk

from ..utils import image_to_array


class BaseWriter:
    def __init__(self, root_directory, filename_format, create_dirs=True):
        self.root_directory = root_directory
        self.filename_format = filename_format
        self.create_dirs = create_dirs
        if create_dirs and not os.path.exists(self.root_directory):
            os.makedirs(self.root_directory)

    def put(self, *args, **kwargs):
        raise NotImplementedError

    def _get_path_from_subject_id(self, subject_id):
        now = datetime.now(timezone.utc)
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H%M%S")
        date_time = date + "_" + time
        out_filename = self.filename_format.format(subject_id=subject_id,
                                                   date=date,
                                                   time=time,
                                                   date_time=date_time)
        out_path = os.path.join(self.root_directory, out_filename)
        out_dir = os.path.dirname(out_path)
        if self.create_dirs and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True) # create subdirectories if specified in filename_format

        return out_path


class ImageFileWriter(BaseWriter):
    def __init__(self, root_directory, filename_format="{subject_id}.nrrd", create_dirs=True, compress=True):
        super().__init__(root_directory, filename_format, create_dirs)
        self.compress = compress

    def put(self, subject_id, image):
        # TODO (Michal) add support for .seg.nrrd files
        out_path = self._get_path_from_subject_id(subject_id)
        sitk.WriteImage(image, out_path, self.compress)


class NumpyWriter(BaseWriter):
    def __init__(self, root_directory, filename_format="{subject_id}.npy", create_dirs=True):
        super().__init__(root_directory, filename_format, create_dirs)
        self.root_directory = root_directory
        self.filename_format = filename_format

    def put(self, subject_id, image):
        out_path = self._get_path_from_subject_id(subject_id)
        if isinstance(image, sitk.Image):
            array, *_ = image_to_array(image) # TODO (Michal) optionally save the image geometry
        np.save(out_path, array)


class HDF5Writer(BaseWriter):
    def __init__(self, root_directory, filename_format="{subject_id}.h5", create_dirs=True, save_geometry=True):
        super().__init__(root_directory, filename_format, create_dirs)
        self.save_geometry = save_geometry

    def put(self, subject_id, metadata=None, **kwargs):
        out_path = self._get_path_from_subject_id(subject_id)
        with h5py.File(out_path, "w") as f:
            for k, v in kwargs.items():
                array, origin, direction, spacing = image_to_array(v)
                dataset = f.create_dataset(k, data=array)
                dataset.attrs.create("subject_id", subject_id)
                if self.save_geometry:
                    dataset.attrs.create("origin", data=origin)
                    dataset.attrs.create("direction", data=direction)
                    dataset.attrs.create("spacing", data=spacing)
            if metadata:
                for k, attrs in metadata.items():
                    for name, v in attrs:
                        f[subject_id].attrs.create(name, data=v)


class MetadataWriter(BaseWriter):
    def __init__(self, root_directory, filename_format="{subject_id}.json", create_dirs=True, remove_existing=True):
        super().__init__(root_directory, filename_format, create_dirs)
        self.file_format = os.path.splitext(filename_format)[1].lstrip(".")
        self.remove_existing = remove_existing
        if self.file_format not in ["json", "csv", "pkl"]:
            raise ValueError(f"File format {self.file_format} not supported. Supported formats: JSON (.json), CSV (.csv), Pickle (.pkl).")

        if self.file_format == "csv" and self.remove_existing:
            out_path = os.path.exists(os.path.join(self.root_directory, self.filename_format))
            if os.path.exists(out_path):
                os.remove(out_path) # remove existing CSV instead of appending

    def _put_json(self, out_path, **kwargs):
        with open(out_path, "w") as f:
            json.dump(kwargs, f)

    def _put_csv(self, out_path, **kwargs):
        with open(out_path, "a+") as f:
            writer = csv.DictWriter(f, fieldnames=kwargs.keys())
            pos = f.tell()
            f.seek(0)
            sample = "\n".join([f.readline() for _ in range(2)])
            if sample == "\n" or not csv.Sniffer().has_header(sample):
                writer.writeheader()
            f.seek(pos)
            writer.writerow(kwargs)

    def _put_pickle(self, out_path, **kwargs):
        with open(out_path, "wb") as f:
            pickle.dump(kwargs, f)

    def put(self, subject_id, **kwargs):
        out_path = self._get_path_from_subject_id(subject_id)

        if "subject_id" not in kwargs:
            kwargs["subject_id"] = subject_id

        if self.file_format == "json":
            self._put_json(out_path, **kwargs)
        elif self.file_format == "csv":
            self._put_csv(out_path, **kwargs)
        elif self.file_format == "pkl":
            self._put_pickle(out_path, **kwargs)
