from __future__ import annotations

import re
from dataclasses import dataclass, field
from itertools import chain
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterator,
    List,
    Mapping,
    Sequence,
    TypeAlias,
)

import numpy as np
import SimpleITK as sitk
from pydicom.dataset import FileDataset
from skimage.draw import polygon2mask

from imgtools import physical_points_to_idxs
from imgtools.exceptions import MissingROIError, ROIContourError
from imgtools.logging import logger
from imgtools.modules.segmentation import Segmentation
from imgtools.modules.structureset import (
    ROI,
    ContourSlice,
    DicomInput,
    RTSTRUCTMetadata,
    extract_rtstruct_metadata,
    load_rtstruct_dcm,
)

if TYPE_CHECKING:
    from pydicom.dataset import FileDataset

# Define type aliases
"""Alias for a string or a list of strings used to represent selection patterns."""
SelectionPattern: TypeAlias = str | List[str] | List[List[str]]

"""Alias for ROI names, which can be:
- SelectionPattern:
    - A single string pattern.
    - A list of string patterns.
- A dictionary mapping strings to patterns or lists of patterns.
- None, to represent the absence of any selection.
"""
ROINamePatterns: TypeAlias = (
    SelectionPattern | Mapping[str, SelectionPattern] | None
)


class ROIExtractionErrorMsg(str):
    pass


class ContourPointsAcrossSlicesError(Exception):
    """Exception raised when contour points span across multiple slices."""

    def __init__(
        self,
        roi_name: str,
        contour_num: int,
        slice_points_shape: tuple,
        z_values: list,
    ) -> None:
        self.roi_name = roi_name
        self.contour_num = contour_num
        self.slice_points_shape = slice_points_shape
        self.z_values = z_values
        super().__init__(self._generate_message())

    def _generate_message(self) -> str:
        return (
            f"Contour points for ROI '{self.roi_name}' and contour {self.contour_num} "
            f"(shape: {self.slice_points_shape}) span across multiple slices: {self.z_values}."
        )


@dataclass
class RTStructureSet:
    """Represents the entire structure set, containing multiple ROIs."""

    # these are the EXTRACTED ROI names, not the original ones in the RTSTRUCT
    # since some will fail to extract
    # missing_rois = set(self.rois.keys()) - set(self.roi_names)
    roi_names: List[str]
    metadata: RTSTRUCTMetadata

    roi_map: dict[str, ROI] = field(repr=False)

    roi_map_errors: dict[str, ROIExtractionErrorMsg] = field(
        repr=False, default_factory=dict
    )

    @property
    def rois(self) -> dict[str, ROI]:
        return {
            roi_name: roi
            for roi_name, roi in self.roi_map.items()
            if isinstance(roi, ROI)
        }

    @classmethod
    def from_dicom(
        cls,
        dicom: DicomInput,
        suppress_warnings: bool = False,
        roi_name_pattern: str | None = None,
        ignore_case: bool = True,
    ) -> RTStructureSet:
        """Create a RTStructureSet object from an RTSTRUCT DICOM file.

        Parameters
        ----------
        dicom : str | Path | bytes | FileDataset
            The RTSTRUCT DICOM object.
        suppress_warnings : bool, optional
            Whether to suppress warnings when extracting ROI points.
            Default is False.
        roi_name_pattern : str, optional
            A regular expression pattern to match ROI names. Default is None.
        ignore_case : bool, optional
            If True, ignore case when matching ROI names. Default is True.

        Returns
        -------
        RTStructureSet
            The structure set data extracted from the RTSTRUCT.
        """
        logger.debug("Loading RTSTRUCT DICOM file.", dicom=dicom)
        dicom_rt: FileDataset = load_rtstruct_dcm(dicom)
        metadata: RTSTRUCTMetadata = extract_rtstruct_metadata(dicom_rt)

        case_ignore = (
            re.IGNORECASE if ignore_case else 0
        )  # for pattern matching

        # Create a dictionary to store the ROI objects
        roi_dict: dict[str, ROI] = {}
        roi_errors: dict[str, ROIExtractionErrorMsg] = {}
        extracted_rois = []  # only track successfully extracted ROIs

        # Extract ROI contour points for each ROI and
        for roi_index, roi_name in enumerate(metadata.OriginalROINames):
            if roi_name_pattern and not re.match(
                roi_name_pattern, roi_name, flags=case_ignore
            ):
                continue
            try:
                extracted_roi = cls._get_roi_points(
                    dicom_rt, roi_index=roi_index, roi_name=roi_name
                )
            except ROIContourError as ae:
                if not suppress_warnings:
                    logger.warning(
                        f"Could not get points for ROI `{roi_name}`.",
                        rtstruct_series=metadata["SeriesInstanceUID"],
                        error=ae,
                    )
                error_string = f"Error extracting ROI '{roi_name}': {ae}"
                roi_errors[roi_name] = ROIExtractionErrorMsg(error_string)
            else:
                roi_dict[roi_name] = extracted_roi
                extracted_rois.append(roi_name)
        logger.debug(
            "Finished extracting ROI points.",
            extracted_rois=extracted_rois,
            failed_rois=list(roi_errors.keys()),
        )
        # Create a new RTStructureSet object
        structure_set = cls(
            roi_map=roi_dict,
            roi_names=extracted_rois,
            roi_map_errors=roi_errors,
            metadata=metadata,
        )

        return structure_set

    def match_roi(
        self, pattern: str, ignore_case: bool = True
    ) -> List[str] | None:
        """Search for ROI names in self.roi_names based on a regular expression pattern.

        Parameters
        ----------
        pattern : str
            The regular expression pattern to search for.
        ignore_case : bool, optional
            Whether to ignore case in the regular expression matching. Default is False.

        Returns
        -------
        List[str] | None
            A list of matching ROI names if any match, None otherwise.

        Examples
        --------
        Assume the following rt has the roi names: ['GTV1', 'GTV2', 'PTV', 'CTV_0', 'CTV_1']
        >>> structure_set = RTStructureSet.from_dicom(
        ...     "path/to/rtstruct.dcm"
        ... )
        >>> structure_set.match_roi("GTV.*")
        ['GTV1', 'GTV2']
        >>> structure_set.match_roi(
        ...     "ctv.*", ignore_case=True
        ... )
        ['CTV_0', 'CTV_1']
        """
        _flags = re.IGNORECASE if ignore_case else 0
        matches = [
            name
            for name in self.roi_names
            if re.fullmatch(pattern=pattern, string=name, flags=_flags)
        ]
        return matches if matches else None

    def __getitem__(self, name: str) -> ROI | list[ROI] | str:
        """Extend slice based access to the data in the RTStructureSet

        rtss = RTStructureSet.from_dicom(...)

        1. rtss['GTV']
            if key exists EXACTLY as 'GTV' in the self.rois dict, return the `ROI` instance
            representing the contour points (sinlge ROI element)
            (maybe we should be returning as a LIST of only 1 element?)
        2. rtss['gtv.*']
            when trying to index using a key that is a regex pattern,
            match the roi names to a pattern that starts with 'gtv' (case-insensitive),
            and if there exists any matched rois, return a `LIST` of `ROI` instances reprensenting
            their contour points.
        3. rtss['PatientID'], or any other attribute of structureset.custom_types.RTSTRUCTMetadata
            if the key is also an attribute of the RTSTRUCTMetadata class, return the value
            of the attribute in the metadata.

        See Also
        --------
        imgtools.modules.structureset.custom_types.ROI
        """
        if name in self.roi_map:
            return self.roi_map[name]
        # Check if name is a pattern and match against ROI names
        elif matched_rois := self.match_roi(name, ignore_case=True):
            return [self.roi_map[roi] for roi in matched_rois]
        elif self.metadata:
            if name in self.metadata:
                return getattr(self.metadata, name)
            else:
                msg = f"{name} not found in ROI names OR metadata."
                msg += f" Available ROIs: {self.roi_names}"
                msg += f" Available metadata: {self.metadata.keys()}"
                raise MissingROIError(msg)
        else:
            errmsg = f"Key `{name}` not found in structure set's ROI names or metadata."
            raise MissingROIError(errmsg)

    def _ipython_key_completions_(self) -> list[str]:
        """IPython/Jupyter tab completion when indexing rtstruct[...]"""
        return list(self.metadata.keys()) + self.roi_names

    def __rich_repr__(self) -> Iterator:
        yield "rois", len(self)  # len(self.roi_names)
        yield "roi_names", ", ".join(self.roi_names)  # self.roi_names
        if self.roi_map_errors:
            yield (
                "failed_roi_extractions",
                ", ".join(self.roi_map_errors.keys()),
            )
        yield "Metadata", self.metadata

    def __len__(self) -> int:
        return len(self.roi_names)

    def __iter__(self) -> Iterator[tuple[str, ROI]]:
        # iterate through self.rois.items if key is in self.roi_names
        for name in self.roi_names:
            yield name, self.roi_map[name]

    def items(self) -> List[tuple[str, ROI]]:
        return list(iter(self))

    @staticmethod
    def _get_roi_points(
        rtstruct: FileDataset, roi_index: int, roi_name: str
    ) -> ROI:
        """Extract and reshapes contour points for a specific ROI in an RTSTRUCT file.

        The passed in roi_index is what is used to index the ROIContourSequence,
        whereas the roi_name is mainly used for debugging, and saved in the returned `ROI`
        instance.

        This method assumes that the order of the rois in dcm.StructureSetROISequence is
        the same order that you will find their corresponding contour data in
        dcm.ROIContourSequence.

        Parameters
        ----------
        rtstruct : FileDataset
            The loaded DICOM RTSTRUCT file.
        roi_index : int
            The index of the ROI in the ROIContourSequence.
        roi_name : str
            The name of the ROI to extract points for.

        Returns
        -------
        imgtools.modules.structureset.ROI (which is a container for List[np.ndarray])
            A list of numpy arrays where each array contains the 3D physical coordinates
            of the contour points for a specific slice.

        Raises
        ------
        ROIContourError
            If the ROIContourSequence, ContourSequence, or ContourData is missing or malformed.

        Examples
        --------
        >>> rtstruct = dcmread(
        ...     "path/to/rtstruct.dcm", force=True
        ... )
        >>> StructureSet._get_roi_points(rtstruct, 0, "GTV")
        """
        # Notes
        # -----
        # The structure of the contour data in the DICOM RTSTRUCT file is as follows:
        # > ROIContourSequence (3006, 0039)
        # >> ReferencedROINumber (3006, 0084)
        # >> ContourSequence (3006, 0040)
        # >>> ContourData (3006, 0050)
        # >>> ContourGeometricType (3006, 0042)
        # >>> NumberOfContourPoints (3006, 0046)

        # Check for ROIContourSequence
        if not hasattr(rtstruct, "ROIContourSequence"):
            raise ROIContourError(
                "The DICOM RTSTRUCT file is missing 'ROIContourSequence'."
            )

        # Check if ROI index exists in the sequence
        if roi_index >= len(rtstruct.ROIContourSequence) or roi_index < 0:
            msg = (
                f"ROI index {roi_index} is out of bounds for the "
                f" 'ROIContourSequence' with length {len(rtstruct.ROIContourSequence)}."
            )
            raise ROIContourError(msg)

        roi_contour = rtstruct.ROIContourSequence[roi_index]

        # Check for ContourSequence in the specified ROI
        if not hasattr(roi_contour, "ContourSequence"):
            msg = (
                f"ROI at index {roi_index}, (ReferencedROINumber={roi_index + 1}) "
                "is missing 'ContourSequence';"
            )
            raise ROIContourError(msg)

        contour_sequence = roi_contour.ContourSequence

        # Check for ContourData in each contour
        contour_points = []
        total_num_points = 0
        contourgeometric_types = set()
        for i, slc in enumerate(contour_sequence):
            if not hasattr(slc, "ContourData"):
                msg = f"Contour {i} in ROI at index {roi_index} is missing 'ContourData'. "
                raise ROIContourError(msg)
            roi_points = np.array(slc.ContourData).reshape(-1, 3)
            contour_slice = ContourSlice(roi_points)
            contour_points.append(contour_slice)
            total_num_points += slc.get("NumberOfContourPoints", 0)
            contourgeometric_types.add(slc.get("ContourGeometricType", None))

        if len(contourgeometric_types) > 1:
            warnmsg = (
                f"Multiple ContourGeometricTypes found for ROI '{roi_name}': "
                f"{contourgeometric_types}."
            )
            logger.warning(warnmsg)
            cgt = ",".join(contourgeometric_types)
        else:
            cgt = contourgeometric_types.pop()

        return ROI(
            name=roi_name,
            ReferencedROINumber=roi_contour.ReferencedROINumber,
            contour_geometric_type=cgt,
            num_points=total_num_points,
            slices=contour_points,
        )

    def summary(self) -> dict:
        """Return a comprehensive summary of the RTStructureSet."""

        roi_info = {}
        for name, roi in self.roi_map.items():
            roi_meta = [
                metadict
                for metadict in self.metadata.OriginalROIMeta
                if metadict["ROIName"] == roi.name
            ]
            roi_info[name] = {
                "ROINumber": roi.ReferencedROINumber,
                "ROIGenerationAlgorithm": roi_meta[0][
                    "ROIGenerationAlgorithm"
                ],
                "ContourGeometricType": roi.contour_geometric_type,
                "NumPoints": roi.num_points,
                "NumSlices": len(roi.slices),
            }

        roi_errors_info = {
            name: str(error) for name, error in self.roi_map_errors.items()
        }
        # remove OriginalROIMeta from metadata
        meta = self.metadata.to_dict()
        meta.pop("OriginalROIMeta", None)
        OriginalNumberOfROIs = meta.pop("OriginalNumberOfROIs", 0)  # noqa

        return {
            "Metadata": meta,
            "OriginalNumberOfROIs": OriginalNumberOfROIs,
            "SuccessfullyExtractedROIs": len(self.roi_names),
            "FailedROIs": len(self.roi_map_errors),
            "ROIInfo": roi_info,
            "ROIErrors": roi_errors_info,
        }

    def _handle_roi_names(
        self, roi_names: ROINamePatterns = None
    ) -> List[str] | None | Mapping[str, List[str] | None]:
        """Handle the ROI names extracted from the RTSTRUCT file."""

        def handle_str_list(
            roi_patterns: SelectionPattern | List[SelectionPattern],
        ) -> List[str] | None:
            match roi_patterns:
                case str() as pattern_str:
                    return self.match_roi(pattern_str)
                case [*roi_pattern_list] if all(
                    isinstance(p, (str, list)) for p in roi_pattern_list
                ):
                    return list(
                        chain.from_iterable(
                            handle_str_list(p) or [] for p in roi_patterns
                        )
                    )
                case _:
                    logger.debug(f"Invalid pattern: {roi_patterns}")
                    return None

        match roi_names:
            case None | []:
                # return all roi names
                return self.roi_names
            case str() as pattern:
                return handle_str_list(pattern)
            case [*roi_pattern_list]:
                return list(
                    chain.from_iterable(
                        handle_str_list(p) for p in roi_pattern_list
                    )
                )
            case dict() as roi_map:
                # raise error if any value is None:
                if None in roi_map.values():
                    raise ValueError(
                        "The 'roi_names' dictionary cannot have any value set to None."
                    )
                map_dict = {}
                for name, pattern in roi_map.items():
                    map_dict[str(name)] = handle_str_list(pattern)
                return map_dict
        return None

    def _get_mask_ndarray(
        self,
        reference_image: sitk.Image,
        ref_img_size: tuple[int, int, int],
        roi_name: str,
        roi_index: int,
        mask_array: np.ndarray,
        continuous: bool,
    ) -> None:
        try:
            roi: ROI = self.roi_map[roi_name]
        except KeyError as ke:
            msg = f"ROI '{roi_name}' not found in the RTSTRUCT file."
            raise MissingROIError(msg) from ke

        logger.debug("Processing ROI.", roi_name=roi_name, roi_index=roi_index)

        roi_slices_as_ndarrays: list[np.ndarray]
        roi_slices_as_ndarrays = [np.asarray(slice_) for slice_ in roi.slices]

        mask_points: list[np.ndarray]
        mask_points = physical_points_to_idxs(
            reference_image, roi_slices_as_ndarrays, continuous=continuous
        )

        for contour_num, contour in enumerate(mask_points, start=0):
            # split the contour into z values and the points
            uniq_z_vals = list(np.unique(contour[:, 0]))
            slice_points = contour[:, 1:]

            match uniq_z_vals:
                # lets make sure that z is 1 unique value
                case [z] if len(uniq_z_vals) == 1:
                    z_idx = z
                case [*z_values]:
                    raise ContourPointsAcrossSlicesError(
                        roi_name,
                        contour_num,
                        slice_points.shape,
                        z_values,
                    )
                case _:
                    errmsg = f"Something went wrong with the contour points {uniq_z_vals}."
                    raise ValueError(errmsg)

            logger.debug(
                f"processing contour {contour_num} for ROI '{roi_name}'",
                z_idx=z_idx,
                slice_points=slice_points.shape,
            )
            filled_mask_array = polygon2mask(ref_img_size[1:], slice_points)

            z_int = int(z_idx)

            # make sure z_int is within the bounds of the mask array
            assert 0 <= z_int < mask_array.shape[0]

            assert (
                0 <= roi_index < mask_array.shape[3]
            )  # Ensure roi_index is within bounds

            try:
                mask_array[z_int, :, :, roi_index] += filled_mask_array
            except IndexError as ie:
                errmsg = f"Error adding mask for ROI '{roi_name}' and contour {contour_num}."
                logger.exception(
                    errmsg,
                    mask_size=mask_array.shape,
                    filled_mask_size=filled_mask_array.shape,
                    z_idx=z_int,
                    roi_index=roi_index,
                )
                raise IndexError(errmsg) from ie

    def get_mask(
        self,
        reference_image: sitk.Image,
        matched_roi_names: List[str] | Mapping[str, List[str]],
        dtype: np.dtype | None = None,
        continuous: bool = False,
    ) -> Segmentation:
        """Generate a binary mask of the specified ROIs.

        Parameters
        ----------
        reference_image : sitk.Image
            The reference image to create the mask from.
        matched_roi_names : ROINamePatterns, optional
            The ROI names to generate the mask for. Default is None.
        dtype : np.dtype, optional
            The data type of the mask image. Default will be np.uint8

        Returns
        -------
        sitk.Image
            The binary mask image.
        """
        if dtype is None:
            dtype = np.dtype(np.uint8)
        seg_roi_indices: dict[str, int] = {}
        ref_img_size = reference_image.GetSize()[::-1]

        mask_img_size = ref_img_size + (len(matched_roi_names),)

        logger.debug(
            "Creating mask array.",
            masksize=mask_img_size,
            refsize=ref_img_size,
            roi_names=matched_roi_names,
        )

        mask_array = np.zeros(mask_img_size, dtype=dtype)

        # i think this is supposed to represent the roi names that were successfully extracted
        raw_roi_names: dict[str, List[str]] = {}
        match matched_roi_names:
            case [*roi_name_list]:
                for idx, roi_name in enumerate(roi_name_list, start=0):
                    self._get_mask_ndarray(
                        reference_image,
                        ref_img_size,
                        roi_name,
                        idx,
                        mask_array,
                        continuous=continuous,
                    )
                    seg_roi_indices[roi_name] = idx
                    raw_roi_names[roi_name] = [roi_name]
            case dict() as roi_map:
                for idx, (roi_id, roi_name_list) in enumerate(
                    roi_map.items(), start=0
                ):
                    raw_roi_names[roi_id] = roi_name_list
                    for roi_name in roi_name_list:
                        self._get_mask_ndarray(
                            reference_image,
                            ref_img_size,
                            roi_name,
                            idx,
                            mask_array,
                            continuous=continuous,
                        )
                        seg_roi_indices[roi_id] = idx

        # create another array where all the values greater than 0 are set to 1
        mask_array_ones = np.where(mask_array > 0, 1, 0)

        mask_image = sitk.GetImageFromArray(mask_array_ones, isVector=True)
        mask_image.CopyInformation(reference_image)

        metadata_summary = self.summary()
        metadata_summary["ROIErrors"] = {
            name: str(error) for name, error in self.roi_map_errors.items()
        }
        metadata_summary["OriginalROINames"] = [
            rm.ROIName for rm in self.metadata.OriginalROIMeta
        ]

        segmentation_object = Segmentation(
            segmentation=mask_image,
            roi_indices=seg_roi_indices,
            raw_roi_names=raw_roi_names,  # type: ignore
            metadata=metadata_summary,
        )
        return segmentation_object


##############################################
# Benchmarking functions


def load_new_rtstruct(file_path: Path) -> RTStructureSet:
    rtstruct = RTStructureSet.from_dicom(file_path)
    return rtstruct


def load_old_rtstruct(file_path: Path) -> StructureSet:
    rtstruct = StructureSet.from_dicom(rtstruct_path=file_path)
    return rtstruct


if __name__ == "__main__":
    import time
    from pathlib import Path

    import pandas as pd
    from rich import print  # noqa

    from imgtools.io.loaders.old_loaders import read_dicom_series
    from imgtools.modules.structureset.structure_set import StructureSet

    index = Path(".imgtools/imgtools_data.csv")

    full_index = pd.read_csv(index, index_col=0)

    df = full_index[full_index["modality"] == "RTSTRUCT"]

    collections = set(df["folder"].apply(lambda x: x.split("/")[1]).tolist())
    print(
        f"There are a total of {len(df)} RTSTRUCT files in the index for {collections} collections."
    )

    # store the metadata for each rtstruct in a dictionary

    # paths = df["file_path"].tolist()
    # logger.setLevel("WARNING")  # type: ignore
    # start_new = time.time()

    # rt = load_new_rtstruct(paths[20])
    # print(rt)

    # print(rt.summary())

    ################################################################
    #
    edges = Path(".imgtools/imgtools_data_edges.csv")

    edge_index = pd.read_csv(edges, index_col=0)

    edge_df = edge_index[
        (edge_index["modality_y"] == "RTSTRUCT")
        & (edge_index["modality_x"] == "CT")
    ]

    rt_paths = edge_df["file_path_y"].tolist()
    ct_paths = edge_df["folder_x"].tolist()

    both_paths = list(zip(rt_paths, ct_paths, strict=True))

    for rt_path, ct_path in both_paths:
        old_rt = load_old_rtstruct(rt_path)
        rt = load_new_rtstruct(rt_path)
        ct_image = read_dicom_series(ct_path)
        print(rt)

        # rt_rois = ["Tumor_c90"]
        rt_p: Dict[str, List[str]] = {
            "Primary": ["Tumor_c90"],
            "Extra": ["LN.*", "Carina.*", "Vertebra.*"],
        }
        rt_rois = rt._handle_roi_names(rt_p)

        # make sure none of the values are None
        if isinstance(rt_rois, dict):
            assert all(rt_rois.values())
            mask = rt.get_mask(ct_image, rt_rois)
        elif isinstance(rt_rois, list):
            mask = rt.get_mask(ct_image, rt_rois)
        print(mask)
        break

    # benchiter = 1
    # for _i in range(benchiter):
    #     for path in paths:
    #         _ = load_new_rtstruct(path)

    # end_new = time.time()

    # start_old = time.time()
    # for _i in range(benchiter):
    #     for path in paths:
    #         __ = load_old_rtstruct(path)
    # end_old = time.time()

    # ##############################
    # # use rich table print to display the results

    # from rich import table as rich_table

    # rtable = rich_table.Table()
    # rtable.add_column("Method", justify="right")
    # rtable.add_column("Time", justify="right")
    # rtable.add_row("New", f"{end_new - start_new:.2f} seconds")
    # rtable.add_row("Old", f"{end_old - start_old:.2f} seconds")

    # print(rtable)
    # for idx, row in df.iterrows():
    #     file_path = row["file_path"]

    #     start = time.time()
    #     rtstruct = RTStructureSet.from_dicom(
    #         file_path,
    #         suppress_warnings=True,
    #     )
    #     print(f"Time taken: {time.time() - start:.2f} seconds")

    #     start = time.time()
    #     rtstruct_old = StructureSet.from_dicom(rtstruct_path=file_path)
    #     print(f"Time taken: {time.time() - start:.2f} seconds")

    #     rt_metadata[file_path] = rtstruct.summary(exclude_errors=False)

    #     print(rtstruct)

    #     break
    # rt_metadata = {}

    # # # vizualize the profiling stats with snakeviz
    # import json

    # rt_metadata_json_path = index.parent / "rt_metadata.json"
    # with rt_metadata_json_path.open("w") as f:
    #     json.dump(rt_metadata, f, indent=4, sort_keys=True)
