from typing import Any, Dict, List, Optional, Sequence, Tuple, TypeVar, Union

import numpy as np
import SimpleITK as sitk

from imgtools.io.loaders import (
    BaseLoader,
)
from imgtools.io.writers import (
    BaseWriter,
)
from imgtools._deprecated import Segmentation, StructureSet, map_over_labels
from imgtools.ops.functional import (
    bounding_box,
    centroid,
    clip_intensity,
    crop,
    crop_to_mask_bounding_box,
    image_statistics,
    min_max_scale,
    resample,
    resize,
    rotate,
    standard_scale,
    window_intensity,
    zoom,
)

# LoaderFunction = TypeVar("LoaderFunction")
# ImageFilter = TypeVar("ImageFilter")
Function = TypeVar("Function")


# Base class
class BaseOp:
    def __call__(self, *args, **kwargs):
        raise NotImplementedError

    def __repr__(self):
        attrs = [
            (k, v) for k, v in self.__dict__.items() if not k.startswith("_")
        ]
        attrs = [
            (k, f"'{v}'") if isinstance(v, str) else (k, v) for k, v in attrs
        ]
        args = ", ".join(f"{k}={v}" for k, v in attrs)
        return f"{self.__class__.__name__}({args})"


# Input/output
class BaseInput(BaseOp):
    def __init__(self, loader):
        if not isinstance(loader, BaseLoader):
            raise ValueError(
                f"loader must be a subclass of io.BaseLoader, got {type(loader)}"
            )
        self._loader = loader

    def __call__(self, key):
        inputs = self._loader.get(key)
        return inputs


class BaseOutput(BaseOp):
    def __init__(self, writer):
        if not isinstance(writer, BaseWriter):
            raise ValueError(
                f"writer must be a subclass of io.BaseWriter, got {type(writer)}"
            )
        self._writer = writer

    def __call__(self, key, *args, **kwargs):
        self._writer.put(key, *args, **kwargs)


class StructureSetToSegmentation(BaseOp):
    """StructureSetToSegmentation operation class:

    A callable class that accepts ROI names, a StructureSet object, and a
    reference image, and returns a Segmentation mask.

    To instantiate:
        obj = StructureSetToSegmentation(roi_names)

    To call:
        mask = obj(structure_set, reference_image)

    Parameters
    ----------
    roi_names : Union[str, List[str], Dict[str, Union[str, List[str]]], None]
        ROI names or patterns to convert to segmentation:
        - `None` (default): All ROIs will be loaded
        - `str`: A single pattern (regex) to match ROI names.
        - `List[str]`: A list of patterns where each matches ROI names.
        - `Dict[str, str | List[str]]`: A dictionary where each key maps to a
          pattern (or list of patterns). The matched names are grouped under
          the same label.
        Both full names and case-insensitive regular expressions are allowed.
    continuous : bool, default=True
        Flag passed to 'physical_points_to_idxs' in 'StructureSet.to_segmentation'.
        Resolves errors caused by ContinuousIndex > Index.

    Notes
    -----
    If `roi_names` contains lists of strings, each matching
    name within a sublist will be assigned the same label. This means
    that `roi_names=['pat']` and `roi_names=[['pat']]` can lead
    to different label assignments, depending on how many ROI names
    match the pattern. E.g. if `self.roi_names = ['fooa', 'foob']`,
    passing `roi_names=['foo(a|b)']` will result in a segmentation with
    two labels, but passing `roi_names=[['foo(a|b)']]` will result in
    one label for both `'fooa'` and `'foob'`.

    If `roi_names` is kept empty ([]), the pipeline will process all ROIs/contours
    found according to their original names.

    In general, the exact ordering of the returned labels cannot be
    guaranteed (unless all patterns in `roi_names` can only match
    a single name or are lists of strings).

    """

    def __init__(
        self,
        roi_names: Union[
            str, List[str], Dict[str, Union[str, List[str]]], None
        ] = None,
        continuous: bool = True,
    ):
        """Initialize the op."""
        self.roi_names = roi_names
        self.continuous = continuous

    def __call__(
        self,
        structure_set: StructureSet,
        reference_image: sitk.Image,
        existing_roi_indices: Dict[str, int],
        ignore_missing_regex: bool,
        roi_select_first: bool = False,
        roi_separate: bool = False,
    ) -> Segmentation | None:
        """Convert the structure set to a Segmentation object.

        Parameters
        ----------
        structure_set
            The structure set to convert.
        reference_image
            Image used as reference geometry.

        Returns
        -------
        Segmentation | None
            The segmentation object.
        """
        return structure_set.to_segmentation(
            reference_image,
            roi_names=self.roi_names,
            continuous=self.continuous,
            existing_roi_indices=existing_roi_indices,
            ignore_missing_regex=ignore_missing_regex,
            roi_select_first=roi_select_first,
            roi_separate=roi_separate,
        )



# class ArrayFunction(BaseOp):
#     """ArrayFunction operation class:
#     A callable class that takes in a function to be used to process an image from numpy array,
#     and executes it.

#     To instantiate:
#         obj = ArrayFunction(function, copy_geometry, **kwargs)
#     To call:
#         result = obj(image)

#     Parameters
#     ----------
#     function
#         A function to be used for image processing.
#         This function needs to have the following signature:
#         - function(image: sitk.Image, **args)
#         - The first argument needs to be an sitkImage, followed by optional arguments.

#     copy_geometry, optional
#         An optional argument to specify whether information about the image should be copied to the
#         resulting image. Set to be true as a default.

#     kwargs, optional
#         Any number of arguements used in the given function.
#     """

#     def __init__(
#         self, function: Function, copy_geometry: bool = True, **kwargs: Optional[Any]
#     ):
#         self.function = function
#         self.copy_geometry = copy_geometry
#         self.kwargs = kwargs

#     def __call__(self, image: sitk.Image) -> sitk.Image:
#         """ArrayFunction callable object:
#         Processes an image from numpy array.

#         Parameters
#         ----------
#         image
#             sitk.Image object to be processed.

#         Returns
#         -------
#         sitk.Image
#             The image processed with a given function.
#         """

#         array, origin, direction, spacing = image_to_array(image)
#         result = self.function(array, **self.kwargs)
#         if self.copy_geometry:
#             result = array_to_image(result, origin, direction, spacing)
#         else:
#             result = array_to_image(result)
#         return result


# Segmentation ops




# class FilterSegmentation:
#     """FilterSegmentation operation class:
#     A callable class that accepts ROI names, a Segmentation mask with all labels
#     and returns only the desired Segmentation masks based on accepted ROI names.

#     To instantiate:
#         obj = StructureSet(roi_names)
#     To call:
#         mask = obj(structure_set, reference_image)

#     Parameters
#     ----------
#     roi_names
#         List of Region of Interests
#     """

#     def __init__(self, roi_patterns: Dict[str, str], continuous: bool = False):
#         """Initialize the op.

#         Parameters
#         ----------
#         roi_names
#             List of ROI names to export. Both full names and
#             case-insensitive regular expressions are allowed.
#             All labels within one sublist will be assigned
#             the same label.

#         """
#         self.roi_patterns = roi_patterns
#         self.continuous = continuous

#     def _assign_labels(
#         self, names, roi_select_first: bool = False, roi_separate: bool = False
#     ):
#         """
#         Parameters
#         ----
#         roi_select_first
#             Select the first matching ROI/regex for each OAR, no duplicate matches.

#         roi_separate
#             Process each matching ROI/regex as individual masks, instead of consolidating into one mask
#             Each mask will be named ROI_n, where n is the nth regex/name/string.
#         """
#         labels = {}
#         cur_label = 0
#         if names == self.roi_patterns:
#             for i, name in enumerate(self.roi_patterns):
#                 labels[name] = i
#         else:
#             for _, pattern in enumerate(names):
#                 if sorted(names) == sorted(
#                     list(labels.keys())
#                 ):  # checks if all ROIs have already been processed.
#                     break
#                 if isinstance(pattern, str):
#                     for i, name in enumerate(self.roi_names):
#                         if re.fullmatch(pattern, name, flags=re.IGNORECASE):
#                             labels[name] = cur_label
#                             cur_label += 1
#                 else:  # if multiple regex/names to match
#                     matched = False
#                     for subpattern in pattern:
#                         if roi_select_first and matched:
#                             break  # break if roi_select_first and we're matched
#                         for n, name in enumerate(self.roi_names):
#                             if re.fullmatch(subpattern, name, flags=re.IGNORECASE):
#                                 matched = True
#                                 if not roi_separate:
#                                     labels[name] = cur_label
#                                 else:
#                                     labels[f"{name}_{n}"] = cur_label

#                     cur_label += 1
#         return labels

#     def get_mask(self, reference_image, seg, mask, label, idx, continuous):
#         size = seg.GetSize()
#         seg_arr = sitk.GetArrayFromImage(seg)
#         if len(size) == 5:
#             size = size[:-1]
#         elif len(size) == 3:
#             size = size.append(1)

#         idx_seg = (
#             self.roi_names[label] - 1
#         )  # SegmentSequence numbering starts at 1 instead of 0
#         if (
#             size[:-1] == reference_image.GetSize()
#         ):  # Assumes `size` is length of 4: (x, y, z, channels)
#             mask[:, :, :, idx] += seg[:, :, :, idx_seg]
#         else:  # if 2D segmentations on 3D images
#             frame = seg.frame_groups[idx_seg]
#             ref_uid = (
#                 frame.DerivationImageSequence[0]
#                 .SourceImageSequence[0]
#                 .ReferencedSOPInstanceUID
#             )  # unused but references InstanceUID of slice
#             assert ref_uid is not None, "There was no ref_uid"  # dodging linter

#             frame_coords = np.array(frame.PlanePositionSequence[0].ImagePositionPatient)
#             img_coords = physical_points_to_idxs(
#                 reference_image, np.expand_dims(frame_coords, (0, 1))
#             )[0][0]
#             z = img_coords[0]

#             mask[z, :, :, idx] += seg_arr[0, idx_seg, :, :]

#     def __call__(
#         self,
#         reference_image: sitk.Image,
#         seg: Segmentation,
#         existing_roi_indices: Dict[str, int],
#         ignore_missing_regex: bool = False,
#         roi_select_first: bool = False,
#         roi_separate: bool = False,
#     ) -> Segmentation:
#         """Convert the structure set to a Segmentation object.

#         Parameters
#         ----------
#         structure_set
#             The structure set to convert.
#         reference_image
#             Image used as reference geometry.

#         Returns
#         -------
#         Segmentation
#             The segmentation object.
#         """
#         from itertools import groupby

#         # variable name isn't ideal, but follows StructureSet.to_segmentation convention
#         self.roi_names = seg.raw_roi_names
#         labels = {}

#         # `roi_names` in .to_segmentation() method = self.roi_patterns
#         if self.roi_patterns is None or self.roi_patterns == {}:
#             self.roi_patterns = self.roi_names
#             labels = self._assign_labels(
#                 self.roi_patterns, roi_select_first, roi_separate
#             )  # only the ones that match the regex
#         elif isinstance(self.roi_patterns, dict):
#             for name, pattern in self.roi_patterns.items():
#                 if isinstance(pattern, str):
#                     matching_names = list(
#                         self._assign_labels([pattern], roi_select_first).keys()
#                     )
#                     if matching_names:
#                         labels[name] = (
#                             matching_names  # {"GTV": ["GTV1", "GTV2"]} is the result of _assign_labels()
#                         )
#                 elif isinstance(
#                     pattern, list
#                 ):  # for inputs that have multiple patterns for the input, e.g. {"GTV": ["GTV.*", "HTVI.*"]}
#                     labels[name] = []
#                     for pattern_one in pattern:
#                         matching_names = list(
#                             self._assign_labels([pattern_one], roi_select_first).keys()
#                         )
#                         if matching_names:
#                             labels[name].extend(
#                                 matching_names
#                             )  # {"GTV": ["GTV1", "GTV2"]}
#         elif isinstance(
#             self.roi_patterns, list
#         ):  # won't this always trigger after the previous?
#             labels = self._assign_labels(self.roi_patterns, roi_select_first)
#         else:
#             raise ValueError(f"{self.roi_patterns} not expected datatype")
#         logger.debug(f"Found {len(labels)} labels", labels=labels)

#         # removing empty labels from dictionary to prevent processing empty masks
#         all_empty = True
#         for v in labels.values():
#             if v != []:
#                 all_empty = False
#         if all_empty:
#             if not ignore_missing_regex:
#                 raise ValueError(
#                     f"No ROIs matching {self.roi_patterns} found in {self.roi_names}."
#                 )
#             else:
#                 return None

#         labels = {k: v for (k, v) in labels.items() if v != []}
#         size = reference_image.GetSize()[::-1] + (len(labels),)
#         mask = np.zeros(size, dtype=np.uint8)

#         seg_roi_indices = {}
#         if self.roi_patterns != {} and isinstance(self.roi_patterns, dict):
#             for i, (name, label_list) in enumerate(labels.items()):
#                 for label in label_list:
#                     self.get_mask(reference_image, seg, mask, label, i, self.continuous)
#                 seg_roi_indices[name] = i
#         else:
#             for name, label in labels.items():
#                 self.get_mask(reference_image, seg, mask, name, label, self.continuous)
#             seg_roi_indices = {
#                 "_".join(k): v for v, k in groupby(labels, key=lambda x: labels[x])
#             }

#         mask[mask > 1] = 1
#         mask = sitk.GetImageFromArray(mask, isVector=True)
#         mask.CopyInformation(reference_image)
#         return Segmentation(
#             mask,
#             roi_indices=seg_roi_indices,
#             existing_roi_indices=existing_roi_indices,
#             raw_roi_names=labels,
#         )


# class MapOverLabels(BaseOp):
#     """MapOverLabels operation class:

#     To instantiate:
#         obj = MapOverLabels(op, include_background, return_segmentation)
#     To call:
#         mask = obj(segmentation, **kwargs)

#     Parameters
#     ----------
#     op
#         A processing function to be used for the operation.

#     """

#     def __init__(
#         self, op, include_background: bool = False, return_segmentation: bool = True
#     ):
#         self.op = op
#         self.include_background = include_background
#         self.return_seg = return_segmentation

#     def __call__(
#         self, segmentation: Segmentation, **kwargs: Optional[Any]
#     ) -> Segmentation:
#         """MapOverLabels callable object:

#         Parameters
#         ----------
#         include_background
#             Specify whether to include background. Set to be false as a default.

#         return_segmentation
#             Specify whether to return segmentation. Set to be true as a default.

#         **kwargs
#             Arguments used for the processing function.

#         Returns
#         -------
#         Segmentation
#             The segmentation mask.
#         """

#         return map_over_labels(
#             segmentation,
#             self.op,
#             include_background=self.include_background,
#             return_segmentation=self.return_seg,
#             **kwargs,
#         )
