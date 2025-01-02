"""
Note from Jermiah:
2025-01-02
- Trying to refactor the writers, but in the interest of not breaking old code, i have kept these
    old writers in the codebase.
- If these are still used in the future, they should be refactored to the new format.
- The new writers should use the AbstractBaseWriter instead
"""

import csv
import json
import os
import pathlib
import pickle

import h5py
import nrrd
import numpy as np
import SimpleITK as sitk
from skimage.measure import regionprops

from imgtools.io.writers.base_classes import BaseWriter
from imgtools.utils import image_to_array


# ruff: noqa
class ImageFileWriter(BaseWriter):
    def __init__(
        self,
        root_directory,
        filename_format="{subject_id}.nii.gz",
        create_dirs=True,
        compress=True,
    ) -> None:
        super().__init__(root_directory, filename_format, create_dirs)
        self.compress = compress

    def put(self, subject_id, image, **kwargs) -> None:
        out_path = self._get_path_from_subject_id(subject_id, **kwargs)
        sitk.WriteImage(image, out_path, self.compress)


class SegNrrdWriter(BaseWriter):
    def __init__(
        self,
        root_directory,
        filename_format="{subject_id}.seg.nrrd",
        create_dirs=True,
        compress=True,
    ) -> None:
        super().__init__(root_directory, filename_format, create_dirs)
        if compress:
            self.compression_level = 9
        else:
            self.compression_level = 1

    def put(self, subject_id, mask, **kwargs) -> None:
        out_path = self._get_path_from_subject_id(subject_id, **kwargs)
        labels = [k for k in mask.roi_names]

        origin = mask.GetOrigin()
        spacing = mask.GetSpacing()
        # direction = mask.GetDirection()

        space = "left-posterior-superior"  # everything is ITK read/write

        # fix reverted somewhere.... :''''(
        space_directions = [
            [spacing[0], 0.0, 0.0],
            [0.0, spacing[1], 0.0],
            [0.0, 0.0, spacing[2]],
        ]
        kinds = ["domain", "domain", "domain"]
        dims = 3

        # permute axes to original orientations
        if len(labels) > 1:
            arr = np.transpose(sitk.GetArrayFromImage(mask), [-1, -2, -3, -4])

            # add extra dimension to metadata
            space_directions.insert(0, [float("nan"), float("nan"), float("nan")])
            kinds.insert(0, "vector")
            dims += 1
        else:
            arr = np.transpose(sitk.GetArrayFromImage(mask), [-1, -2, -3])

        # ensure proper conversion to array
        assert mask.GetSize() == arr.shape[-3:]

        segment_info = {}
        for n, i in enumerate(labels):
            try:
                props = (
                    regionprops(arr[n])[0] if len(labels) > 1 else regionprops(arr)[0]
                )
                bbox = props["bbox"]
                bbox_segment = [bbox[0], bbox[3], bbox[1], bbox[4], bbox[2], bbox[5]]
            except IndexError:  # mask is empty
                assert (
                    arr[n].sum() == 0
                ), "Mask not empty but 'skimage.measure.regionprops' failed."
                bbox_segment = [0, 0, 0, 0, 0, 0]

            segment_info[f"Segment{n}_Color"] = list(np.random.random(3))
            segment_info[f"Segment{n}_ColorAutoGenerated"] = "1"
            segment_info[f"Segment{n}_Extent"] = bbox_segment
            segment_info[f"Segment{n}_ID"] = str(n)
            segment_info[f"Segment{n}_Name"] = i
            segment_info[f"Segment{n}_NameautoGenerated"] = "0"

        header = {
            "dimension": dims,
            "space": space,
            "sizes": mask.GetSize(),
            "space directions": space_directions,
            "kinds": kinds,
            "endian": "little",
            "space origin": origin,
            "roi_names": labels,
            **segment_info,
        }

        nrrd.write(
            out_path,
            arr,
            header=header,
            compression_level=self.compression_level,
            **kwargs,
        )


class NumpyWriter(BaseWriter):
    def __init__(
        self, root_directory, filename_format="{subject_id}.npy", create_dirs=True
    ) -> None:
        super().__init__(root_directory, filename_format, create_dirs)
        self.root_directory = root_directory
        self.filename_format = filename_format

    def put(self, subject_id, image, **kwargs) -> None:
        out_path = self._get_path_from_subject_id(subject_id, **kwargs)
        if isinstance(image, sitk.Image):
            array, *_ = image_to_array(
                image
            )  # TODO (Michal) optionally save the image geometry
        np.save(out_path, array)


class HDF5Writer(BaseWriter):
    def __init__(
        self,
        root_directory,
        filename_format="{subject_id}.h5",
        create_dirs=True,
        save_geometry=True,
    ) -> None:
        super().__init__(root_directory, filename_format, create_dirs)
        self.save_geometry = save_geometry

    def put(self, subject_id, images, metadata=None, **kwargs) -> None:
        out_path = self._get_path_from_subject_id(subject_id, **kwargs)
        with h5py.File(out_path, "w") as f:
            if not isinstance(images, dict):
                images = {"image": images}
            for k, v in images.items():
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
    def __init__(
        self,
        root_directory,
        filename_format="{subject_id}.json",
        create_dirs=True,
        remove_existing=True,
    ) -> None:
        super().__init__(root_directory, filename_format, create_dirs)
        self.file_format = os.path.splitext(filename_format)[1].lstrip(".")
        self.remove_existing = remove_existing
        if self.file_format not in ["json", "csv", "pkl"]:
            msg = f"File format {self.file_format} not supported. Supported formats: JSON (.json), CSV (.csv), Pickle (.pkl)."
            raise ValueError(msg)

        if self.file_format == "csv" and self.remove_existing:
            out_path = pathlib.Path(
                self.root_directory, self.filename_format
            ).as_posix()
            if os.path.exists(out_path):
                os.remove(out_path)  # remove existing CSV instead of appending

    def _put_json(self, out_path, **kwargs) -> None:
        with open(out_path, "w") as f:
            json.dump(kwargs, f)

    def _put_csv(self, out_path, **kwargs) -> None:
        with open(out_path, "a+") as f:
            writer = csv.DictWriter(f, fieldnames=kwargs.keys())
            pos = f.tell()
            f.seek(0)
            sample = "\n".join([f.readline() for _ in range(2)])
            if sample == "\n" or not csv.Sniffer().has_header(sample):
                writer.writeheader()
            f.seek(pos)
            writer.writerow(kwargs)

    def _put_pickle(self, out_path, **kwargs) -> None:
        with open(out_path, "wb") as f:
            pickle.dump(kwargs, f)

    def put(self, subject_id, **kwargs) -> None:
        out_path = self._get_path_from_subject_id(subject_id)

        if "subject_id" not in kwargs:
            kwargs["subject_id"] = subject_id

        if self.file_format == "json":
            self._put_json(out_path, **kwargs)
        elif self.file_format == "csv":
            self._put_csv(out_path, **kwargs)
        elif self.file_format == "pkl":
            self._put_pickle(out_path, **kwargs)
