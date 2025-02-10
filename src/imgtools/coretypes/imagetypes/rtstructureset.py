from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass, field
from enum import Enum
from itertools import chain
from typing import (
    TYPE_CHECKING,
    Iterator,
    List,
    Mapping,
    Sequence,
    TypeAlias,
)

import numpy as np
from pydicom.dataset import FileDataset
from skimage.draw import polygon2mask

from imgtools.dicom import (
    load_rtstruct_dcm,
    rtstruct_reference_uids,
)
from imgtools.exceptions import (
    MissingROIError,
    ROIContourError,
)
from imgtools.logging import logger
from imgtools.utils import DataclassMixin, physical_points_to_idxs

if TYPE_CHECKING:
    import SimpleITK as sitk
    from pydicom import FileDataset

    from imgtools.dicom import DicomInput


__all__ = [
    "SelectionPattern",
    "ROINamePatterns",
    "ROIContourGeometricType",
    "ContourPointsAcrossSlicesError",
    "ROI",
    "RTStructureSetMetadata",
    "RTStructureSet",
    "load_rtstructureset",
]

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


class ROIContourGeometricType(str, Enum):
    """Enum for the geometric types of ROI contours."""

    # https://dicom.nema.org/medical/Dicom/2018d/output/chtml/part03/sect_C.8.8.6.html#sect_C.8.8.6.1
    POINT = "POINT"
    OPEN_PLANAR = "OPEN_PLANAR"
    CLOSED_PLANAR = "CLOSED_PLANAR"
    OPEN_NONPLANAR = "OPEN_NONPLANAR"


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
class ROI(DataclassMixin):
    """Dataclass for ROI metadata.

    New keys can be added as needed.
    """

    ROIName: str
    ROINumber: str
    ReferencedFrameOfReferenceUID: str
    ROIGenerationAlgorithm: str | None = field(default=None)
    ContourGeometricType: ROIContourGeometricType | None = field(default=None)
    ContourSequence: Sequence = field(default_factory=list)

    @classmethod
    def from_dicom(cls, rtstruct: FileDataset) -> List[ROI]:
        _roi_mapping = {
            contour_meta.ROINumber: contour_meta
            for contour_meta in rtstruct.StructureSetROISequence
        }

        _contour_mapping = {
            contour_sequence.ReferencedROINumber: contour_sequence
            for contour_sequence in rtstruct.ROIContourSequence
        }

        assert len(_roi_mapping) == len(_contour_mapping), (
            "Number of ROIs and contours do not match."
            f"ROIs: {len(_roi_mapping)}, Contours: {len(_contour_mapping)}"
        )

        rois: List[ROI] = []

        for roi_number, roi_meta in _roi_mapping.items():
            if roi_number not in _contour_mapping:
                msg = f"ROI {roi_number} is missing from the contour sequence."
                raise MissingROIError(msg)

            contour_sequence = _contour_mapping[roi_number]
            if not (
                hasattr(contour_sequence, "ContourSequence")
                and len(contour_sequence.ContourSequence)
            ):
                # msg = f"ROI {roi_number} is missing contour data."
                # logger.warning(msg)
                continue

            roi = ROI(
                ROIName=roi_meta.ROIName,
                ROINumber=roi_meta.ROINumber,
                ReferencedFrameOfReferenceUID=roi_meta.ReferencedFrameOfReferenceUID,
                ROIGenerationAlgorithm=roi_meta.ROIGenerationAlgorithm,
                ContourGeometricType=ROIContourGeometricType(
                    contour_sequence.ContourSequence[0].ContourGeometricType
                ),
                ContourSequence=contour_sequence.ContourSequence,
            )
            rois.append(roi)

        return rois


@dataclass
class RTStructureSetMetadata(DataclassMixin):
    PatientID: str
    Modality: str
    StudyInstanceUID: str
    SeriesInstanceUID: str
    ReferencedStudyInstanceUID: str
    ReferencedSeriesInstanceUID: str

    # implement dict-like 'update' method
    def update(self, **kwargs: str) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def from_dicom(cls, dicom: DicomInput) -> RTStructureSetMetadata:
        rtstruct: FileDataset = load_rtstruct_dcm(dicom)

        ref_series, ref_study = rtstruct_reference_uids(rtstruct)
        metadata = RTStructureSetMetadata(
            PatientID=rtstruct.PatientID,
            Modality=rtstruct.Modality,
            StudyInstanceUID=rtstruct.StudyInstanceUID,
            SeriesInstanceUID=rtstruct.SeriesInstanceUID,
            ReferencedStudyInstanceUID=ref_study,
            ReferencedSeriesInstanceUID=ref_series,
        )
        return metadata


@dataclass
class RTStructureSet(DataclassMixin):
    """Represents the entire structure set, containing multiple ROIs."""

    metadata: RTStructureSetMetadata
    rois: dict[str, ROI] = field(default_factory=dict, repr=False)

    @property
    def roi_names(self) -> List[str]:
        """Return a list of ROI names in the structure set."""
        return list(self.rois.keys())

    @classmethod
    def from_dicom(
        cls,
        dicom: DicomInput,
    ) -> RTStructureSet:
        """Create a RTStructureSet object from an RTSTRUCT DICOM file.

        Parameters
        ----------
        dicom : str | Path | bytes | FileDataset
            The RTSTRUCT DICOM object.
        Returns
        -------
        RTStructureSet
            The structure set data extracted from the RTSTRUCT.
        """
        logger.debug("Loading RTSTRUCT DICOM file.", dicom=dicom)
        dicom_rt: FileDataset = load_rtstruct_dcm(dicom)
        metadata: RTStructureSetMetadata = RTStructureSetMetadata.from_dicom(
            dicom_rt
        )
        if isinstance(dicom, (str, pathlib.Path)):
            metadata.update(filepath=str(dicom))
        rois = {roi.ROIName: roi for roi in ROI.from_dicom(dicom_rt)}
        return cls(metadata=metadata, rois=rois)

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
            for name in self.roi_names  # same as self.rois.keys()
            if re.fullmatch(pattern=pattern, string=name, flags=_flags)
        ]
        return matches if matches else None

    def __len__(self) -> int:
        return len(self.roi_names)

    def __iter__(self) -> Iterator[tuple[str, ROI]]:
        # iterate through self.rois.items if key is in self.roi_names
        for name in self.roi_names:
            yield name, self.rois[name]

    def items(self) -> List[tuple[str, ROI]]:
        return list(iter(self))

    def _get_contour_data(self, roi_name: str) -> List[np.ndarray]:
        """Get contour data for a specific ROI.

        Parameters
        ----------
        roi_name : str
            The name of the ROI to get contour data for.

        Returns
        -------
        dict
            A dictionary containing contour data for the specified ROI.
        """
        roi = self.rois.get(roi_name)
        if roi is None:
            msg = f"ROI '{roi_name}' not found in the structure set."
            raise MissingROIError(msg)

        _roi_ndarray: List[np.ndarray] = []
        for slc in roi.ContourSequence:
            if not hasattr(slc, "ContourData"):
                msg = (
                    "ContourData not found for ROI "
                    f"'{roi['ROIName']}' (#{roi['ROINumber']})."
                )
                raise ROIContourError(msg)

            _roi_ndarray.append(np.array(slc.ContourData).reshape(-1, 3))

        return _roi_ndarray

    def _get_mask_ndarray(
        self,
        reference_image: sitk.Image,
        ref_img_size: tuple[int, int, int],
        roi_name: str,
        roi_index: int,
        mask_array: np.ndarray,
        continuous: bool,
    ) -> None:
        roi_contour_data: List[np.ndarray] = self._get_contour_data(roi_name)

        logger.debug("Processing ROI.", roi_name=roi_name, roi_index=roi_index)
        mask_points: list[np.ndarray]
        mask_points = physical_points_to_idxs(
            reference_image, roi_contour_data, continuous=continuous
        )

        # contour_num is not guaranteed to be the same as ROINumber!
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

    def _handle_roi_names(
        self, roi_names: ROINamePatterns = None
    ) -> List[str] | None | Mapping[str, List[str] | None]:
        """Handle the ROI names extracted from the RTSTRUCT file."""

        def handle_str_list(
            roi_patterns: SelectionPattern | List[SelectionPattern],
        ) -> List[str] | None:
            """Helper to handle string or list of strings."""
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
                        handle_str_list(p) or [] for p in roi_pattern_list
                    )
                )
            case dict() as roi_map:
                # raise error if any value is None:
                if None in roi_map.values():
                    errmsg = "The 'roi_names' dictionary cannot have any value set to None."
                    raise ValueError(errmsg)
                map_dict = {}
                for name, pattern in roi_map.items():
                    map_dict[str(name)] = handle_str_list(pattern)
                return map_dict
        return None


def load_rtstructureset(dicom: DicomInput) -> RTStructureSet:
    """Load an RTSTRUCT DICOM file and return the RTStructureSet object.

    Parameters
    ----------
    dicom : str | Path | bytes | FileDataset
        The RTSTRUCT DICOM object.

    Returns
    -------
    RTStructureSet
        The structure set data extracted from the RTSTRUCT.
    """
    return RTStructureSet.from_dicom(dicom)


if __name__ == "__main__":  # pragma: no cover
    from rich import print  # noqa
    import pandas as pd

    # from tqdm import tqdm
    import time
    from imgtools.modules import StructureSet

    # rtp = "data/4D-Lung/113_HM10395/2.25.186899387610254289948150314209581209847.5/00000001.dcm"
    moredata = pathlib.Path(
        "/home/jermiah/bhklab/radiomics/readii-negative-controls/rawdata"
    )
    # HEAD-NECK-RADIOMICS-HN1  HNSCC  RADCURE
    datasets = ["HEAD-NECK-RADIOMICS-HN1", "HNSCC", "RADCURE"]
    all_paths: list[pathlib.Path] = []
    for ds in datasets:
        imgtool_dir = moredata / ds / "images" / ".imgtools"
        imgtools_file = imgtool_dir / "imgtools_dicoms.csv"
        df = pd.read_csv(imgtools_file)
        rt_df = df[df["modality"] == "RTSTRUCT"]
        print(f"RTSTRUCT files: {len(rt_df)} for {ds}")

        # all_df = pd.concat([all_df, rt_df])
        paths = [imgtool_dir.parent / fp for fp in rt_df["file_path"].values]
        assert all([p.exists() for p in paths])

        all_paths.extend(paths)

    imgtools_file = pathlib.Path(".imgtools/imgtools_data.csv")
    df = pd.read_csv(imgtools_file)
    rt_df = df[df["modality"] == "RTSTRUCT"]

    all_paths.extend(
        [pathlib.Path.cwd() / p for p in rt_df["file_path"].values]
    )

    print(f"RTSTRUCT files: {len(rt_df)}")

    print(f"All RTSTRUCT files: {len(all_paths)}")

    subset_paths = all_paths[:100]
    logger.setLevel("WARNING")  # type: ignore

    def run(subset_paths, setting) -> None:  # noqa
        start = time.time()

        if setting == 1:
            rts = [RTStructureSet.from_dicom(rtp) for rtp in subset_paths]
            # for rt in rts:
            #     for rn in rt.roi_names:
            #         _ = rt._get_contour_data(rn)
        elif setting == 2:
            _ = [
                StructureSet.from_dicom(rtp, suppress_warnings=True)
                for rtp in subset_paths
            ]
        print(f"Time taken: {time.time() - start:.2f}s for setting {setting}")

    run(subset_paths, setting=1)
    run(subset_paths, setting=2)

    # for rt in tqdm(rt_df["file_path"].values):
    #     try:
    #         rtstruct = RTStructureSet.from_dicom(rt)
    #         # print(rtstruct)
    #     except (MissingROIError, ROIContourError, RTSTRUCTAttributeError) as e:
    #         logger.error(f"Error processing {rt} - {e}")
    #         continue
    #     except Exception as e:
    #         logger.error(f"Error processing {rt} - {e}")
    #         continue
