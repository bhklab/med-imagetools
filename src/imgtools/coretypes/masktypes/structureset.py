from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
)

import numpy as np
import SimpleITK as sitk
from pydicom.dataset import FileDataset
from skimage.draw import polygon2mask

from imgtools.coretypes.imagetypes import MedImage
from imgtools.coretypes.masktypes.roi_matching import (
    ROI_HANDLING,
    ROIMatcher,
)
from imgtools.dicom import DicomInput, load_dicom
from imgtools.dicom.dicom_metadata import extract_metadata
from imgtools.exceptions import (
    ContourPointsAcrossSlicesError,
    MissingROIError,
    ROIContourError,
)
from imgtools.loggers import logger
from imgtools.utils import physical_points_to_idxs

if TYPE_CHECKING:
    from pydicom.dataset import FileDataset
    from pydicom.sequence import Sequence


class ROIExtractionErrorMsg(str):
    pass


ROIMaskMapping = namedtuple("ROIMaskMapping", ["roi_key", "roi_names"])


@dataclass
class RTStructureSet:
    """Represents the entire structure set, containing multiple ROIs.

    Attributes
    ----------
    roi_names : List[str]
        List of ROI names extracted from the RTSTRUCT.
    metadata : dict[str, Any]
        Metadata extracted from the RTSTRUCT DICOM file.
    roi_map : dict[str, ROI]
        Dictionary mapping ROI names to their corresponding `ROI` objects.
    roi_map_errors : dict[str, ROIExtractionErrorMsg]
        Dictionary mapping ROI names to any extraction errors encountered.

    Methods
    -------
    from_dicom(dicom: DicomInput) -> RTStructureSet
        Create a `RTStructureSet` object from a DICOM file.
    match_roi(pattern: str, ignore_case: bool = True) -> List[str] | None
        Search for ROI names matching a given pattern.
    __getitem__(idx: str | int | slice) -> ROI | List[ROI]
        Access ROI objects by name, index, or slice.
    summary() -> dict
        Return a comprehensive summary of the RTStructureSet.
    """

    # these are the EXTRACTED ROI names, not the original ones in the RTSTRUCT
    # since some will fail to extract
    metadata: dict[str, Any] = field(repr=False)
    roi_names: List[str] = field(
        default_factory=list,
        init=False,
    )
    roi_map: dict[str, Sequence] = field(
        repr=False,
        default_factory=dict,
    )
    roi_map_errors: dict[str, ROIExtractionErrorMsg] = field(
        repr=False, default_factory=dict, init=False
    )

    # store a hidden cache to store the numpy arrays
    # after the first time we access them
    _roi_cache: dict[str, np.ndarray] = field(
        repr=False,
        default_factory=dict,
        init=False,
    )

    @classmethod
    def from_dicom(
        cls,
        dicom: DicomInput,
        suppress_warnings: bool = False,
    ) -> RTStructureSet:
        """Create a RTStructureSet object from an RTSTRUCT DICOM file.

        Lazy loads by default, by giving access to ROI Names and metadata
        and then loads the ROIs on demand. See Notes.

        Parameters
        ----------
        dicom : str | Path | bytes | FileDataset
            The RTSTRUCT DICOM object.
        suppress_warnings : bool, optional
            Whether to suppress warnings when extracting ROI points.
            Default is False.
        Returns
        -------
        RTStructureSet
            The structure set data extracted from the RTSTRUCT.

        Notes
        -----
        Compared to the old implementation, we dont extract the numpy arrays
        for the ROIs immediately. Instead, we just extract the metadata and
        then store the weak-refs to the `ROIContourSequence` objects.
        This allows us to avoid the computation of the numpy arrays until we
        actually ask for them (i.e converting to `sitk.Image`) which might
        use some regex pattern matching to only process the ROIs that
        we want.
        """
        if isinstance(dicom, (str, Path)):
            dicom = Path(dicom)
            if dicom.is_dir():
                if len(list(dicom.glob("*.dcm"))) == 1:
                    dicom = list(dicom.glob("*.dcm"))[0]
                else:
                    errmsg = (
                        f"Directory `{dicom}` contains multiple DICOM files. "
                    )
                    raise ValueError(errmsg)

        # logger.debug("Loading RTSTRUCT DICOM file.", dicom=dicom)
        dicom_rt: FileDataset = load_dicom(dicom)
        metadata: Dict[str, Any] = extract_metadata(
            dicom_rt, "RTSTRUCT", extra_tags=None
        )
        rt = cls(
            metadata=metadata,
        )

        # Extract ROI contour points for each ROI and
        for roi_index, roi_name in enumerate(metadata["ROINames"]):
            try:
                extracted_roi: Sequence = cls._get_roi_points(
                    dicom_rt, roi_index=roi_index
                )
            except ROIContourError as ae:
                if not suppress_warnings:
                    logger.warning(
                        f"Could not get points for ROI `{roi_name}`.",
                        rtstruct_series=metadata["SeriesInstanceUID"],
                        error=ae,
                    )
                error_string = f"Error extracting ROI '{roi_name}': {ae}"
                rt.roi_map_errors[roi_name] = ROIExtractionErrorMsg(
                    error_string
                )
            else:
                rt.roi_map[roi_name] = extracted_roi
                rt.roi_names.append(roi_name)

        return rt

    @staticmethod
    def _get_roi_points(rtstruct: FileDataset, roi_index: int) -> Sequence:
        """Extract and reshapes contour points for a specific ROI in an RTSTRUCT file.
        The passed in roi_index is what is used to index the ROIContourSequence,
        whereas the roi_name is mainly used for debugging purposes.


        This method assumes that the order of the rois in dcm.StructureSetROISequence is
        the same order that you will find their corresponding contour data in
        dcm.ROIContourSequence.

        Parameters
        ----------
        rtstruct : FileDataset
            The loaded DICOM RTSTRUCT file.
        roi_index : int
            The index of the ROI in the ROIContourSequence.

        Returns
        -------
        Sequence
            The contour points as the
            `rtstruct.ROIContourSequence[roi_index].ContourSequence`

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

        # Check for ContourSequence in the specified ROI
        if not hasattr(
            roi_contour := rtstruct.ROIContourSequence[roi_index],
            "ContourSequence",
        ):
            msg = (
                f"ROI at index {roi_index}, (ReferencedROINumber={roi_index + 1}) "
                "is missing 'ContourSequence';"
            )
            raise ROIContourError(msg)

        if len(roi_contour.ContourSequence) == 0:
            msg = (
                f"ROI at index {roi_index}, (ReferencedROINumber={roi_index + 1}) "
                "has an empty 'ContourSequence'."
            )
            raise ROIContourError(msg)

        # Sometimes the contour could be a POINT or just broken
        # and not have a ContourData
        # Check for ContourData in the first contour
        if not hasattr(roi_contour.ContourSequence[0], "ContourData"):
            msg = f"ContourSequence in ROI at index {roi_index} is missing 'ContourData'. "
            raise ROIContourError(msg)

        return roi_contour.ContourSequence

    def __getitem__(self, idx: str | int | slice) -> Sequence | List[Sequence]:
        """Extend slice based access to the data in the RTStructureSet
        rtss = RTStructureSet.from_dicom(...)
        - rtss['GTV'] -> ROI instance
            if key exists EXACTLY as 'GTV' in the self.rois dict, return the `ROI` instance
            representing the contour points (sinlge ROI element)
            (maybe we should be returning as a LIST of only 1 element?)
        - rtss[0] -> ROI instance
            if key is an integer, return the `ROI` instance at that index
        - rtss[0:2] -> List[ROI] instance
        """
        match idx:
            case int():
                # Return the ROI at the specified index
                return self.roi_map[self.roi_names[idx]]
            case slice():
                # Return a list of ROIs for the specified slice
                return [self.roi_map[name] for name in self.roi_names[idx]]
            case str():
                # Check if the name exists in the roi_names
                if idx in self.roi_names:
                    return self.roi_map[idx]
                else:
                    errmsg = (
                        f"Key `{idx}` not found in structure set's ROI names"
                    )
            case _:
                errmsg = (
                    f"Key `{idx}` of type {type(idx)} not supported. "
                    "Expected int, slice, or str."
                )
        raise MissingROIError(errmsg)

    def _ipython_key_completions_(self) -> list[str]:  # pragma: no cover
        """IPython/Jupyter tab completion when indexing rtstruct[...]"""
        return self.roi_names

    def summary(self) -> dict:
        """Return a comprehensive summary of the RTStructureSet."""

        roi_errors_info = {
            name: str(error) for name, error in self.roi_map_errors.items()
        }

        # ignore iroi names because we already have them in roi_map
        meta = {
            k: v for k, v in self.metadata.copy().items() if k != "ROINames"
        }

        return {
            "Metadata": meta,
            "ROI Details": self.roi_map,
            "ROIErrors": roi_errors_info,
        }

    def __len__(self) -> int:
        return len(self.roi_names)

    def get_mask_ndarray(
        self,
        reference_image: MedImage,
        roi_name: str,
        mask_img_size: tuple[int, int, int, int],
        continuous: bool = True,
    ) -> np.ndarray:
        if roi_name in self._roi_cache:
            return self._roi_cache[roi_name]

        try:
            roi = self.roi_map[roi_name]
        except KeyError as ke:
            msg = f"ROI '{roi_name}' not found in RTSTRUCT."
            raise MissingROIError(msg) from ke

        slices = [np.array(slc.ContourData).reshape(-1, 3) for slc in roi]

        mask_points = physical_points_to_idxs(
            reference_image, slices, continuous=continuous
        )

        mask_array_3d = np.zeros(
            mask_img_size[0:3],
            dtype=np.uint8,
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

            filled_mask_array = polygon2mask(
                mask_img_size[1:3],
                slice_points,
            )

            z_int = int(z_idx)

            # make sure z_int is within the bounds of the mask array
            assert 0 <= z_int < mask_array_3d.shape[0], (
                f"z_int {z_int} ({z_idx=}) is out of bounds for mask array "
                f"with shape {mask_array_3d.shape=}."
                f" ROI: {roi_name}, "
                f"ContourNum: {contour_num}, "
                f"ContourPoints: {slice_points.shape}, "
                f"ZValues: {uniq_z_vals}"
            )
            mask_array_3d[z_int, :, :] = np.logical_or(
                mask_array_3d[z_int, :, :], filled_mask_array
            )

        # Store the mask in the cache
        self._roi_cache[roi_name] = mask_array_3d

        return mask_array_3d

    def get_label_mask(
        self,
        reference_image: MedImage,
        roi_matcher: ROIMatcher,
        continuous: bool = True,
    ) -> tuple[sitk.Image, dict[int, ROIMaskMapping]]:
        matched_rois: list[tuple[str, list[str]]] = roi_matcher.match_rois(
            self.roi_names
        )
        if not matched_rois:
            errmsg = (
                f"No matching ROIs found. Available ROIs: {self.roi_names}, "
            )
            raise MissingROIError(errmsg)

        logger.debug("Matched ROIs", matched_rois=matched_rois)

        ref_size = reference_image.size
        mask_img_size: tuple[int, int, int, int] = (
            ref_size.depth,
            ref_size.height,
            ref_size.width,
            len(matched_rois),
        )

        mask_array_4d = np.zeros(
            mask_img_size,
            dtype=np.uint8,
        )

        # lets make sure the shape is 4D
        assert mask_array_4d.ndim == 4

        # we need something to store the mapping
        # so that we can keep track of what the 3D mask matches to
        # the original roi name(s)
        mapping: dict[int, ROIMaskMapping] = {}

        for iroi, (roi_key, matches) in enumerate(matched_rois):
            logger.debug(
                f"Processing {roi_key=} ({iroi + 1}/{len(matched_rois)})",
                matches=matches,
            )
            match matches:
                case [*many_rois]:
                    # most likely handle type MERGE
                    for roi_name in many_rois:
                        mask_3d = self.get_mask_ndarray(
                            reference_image,
                            roi_name,
                            mask_img_size,
                            continuous=continuous,
                        )
                    # here we want to combine the masks in the same 4th dimension
                    mask_array_4d[:, :, :, iroi] = np.logical_or(
                        mask_array_4d[:, :, :, iroi], mask_3d
                    )
                    mapping[iroi] = ROIMaskMapping(
                        roi_key=roi_key,
                        roi_names=many_rois,
                    )

                case str():
                    mask_3d = self.get_mask_ndarray(
                        reference_image,
                        matched_rois,
                        mask_img_size,
                        continuous=continuous,
                    )
                    # here each roi is in its own 4th dimension
                    mask_array_4d[:, :, :, iroi] = mask_3d
                    mapping[iroi] = ROIMaskMapping(
                        roi_key=roi_key,
                        roi_names=[roi_key],
                    )

        # convert to sitk image
        mask_image = sitk.GetImageFromArray(mask_array_4d, isVector=True)
        mask_image.CopyInformation(reference_image)

        assert mask_image.GetPixelIDValue() == 13
        assert mask_image.GetNumberOfComponentsPerPixel() == len(matched_rois)

        return mask_image, mapping


if __name__ == "__main__":  # pragma: no cover
    from rich import print  # noqa
    import pandas as pd  # noqa
    from imgtools.coretypes.imagetypes.scan import read_dicom_scan
    from tqdm import tqdm  # noqa
    from imgtools.loggers import tqdm_logging_redirect

    index = Path(".imgtools/data/index.csv")

    index_df = pd.read_csv(index)

    # remove dupicate rows
    index_df = index_df.drop_duplicates(subset=["SeriesInstanceUID"])

    index_df = index_df.set_index("SeriesInstanceUID", drop=False)
    rtstructs = index_df.query("Modality == 'RTSTRUCT'")

    results = []
    failures = []
    failed = [
        "1.3.6.1.4.1.14519.5.2.1.262731039041525300359366945100409730057",
        "1.3.6.1.4.1.14519.5.2.1.145604855576133072144485190249196760430",
        "1.3.6.1.4.1.14519.5.2.1.161876574066675833575211443252309034265",
        "1.3.6.1.4.1.14519.5.2.1.303606626100058921970651747217776792853",
        "1.3.6.1.4.1.14519.5.2.1.239064923357616718786196407609276882856",
        "1.3.6.1.4.1.14519.5.2.1.75164064738538288645257513911612519591",
        "1.3.6.1.4.1.14519.5.2.1.100364245183930759730290495595573094436",
    ]
    with tqdm_logging_redirect():
        for _, row in tqdm(
            rtstructs.iterrows(),
            total=len(rtstructs),
            desc="Processing RTSTRUCTs",
        ):
            if row["SeriesInstanceUID"] not in failed:
                continue

            refrow = index_df.loc[str(row.loc["ReferencedSeriesUID"])]
            if refrow is None:
                continue

            ref_image = read_dicom_scan(
                path=str(refrow.loc["folder"]),
                series_id=str(refrow.loc["SeriesInstanceUID"]),
            )
            rtstruct = RTStructureSet.from_dicom(row["folder"])

            for strategy in [
                ROI_HANDLING.MERGE,
                # ROI_HANDLING.SEPARATE,
                # ROI_HANDLING.KEEP_FIRST,
            ]:
                matcher = ROIMatcher(
                    # https://www.aapm.org/pubs/reports/RPT_263.pdf align later
                    roi_map={
                        "GTV": [r"gtv.*", r"g.*tv.*"],
                        "CTV": [r"ctv.*"],
                        "PTV": [r"PTV.*", r"total PTV", r"uni.*"],
                        "Tumor": [r"tumor.*", "gtv.*", "oar.*"],
                        "Brain": [r"brain.*"],
                        "Prostate": [r"prostate.*"],
                        "Femur": [r"femur.*"],
                        "Bladder": [r"bladder.*"],
                        "Rectum": [r"rectum.*"],
                        "Lung": [r"lung.*"],
                        "Heart": [r"heart.*"],
                        "Liver": [r"liver.*"],
                        "Kidney": [r"kidney.*"],
                        "Cochlea": [r"cochlea.*"],
                        # ??? ['Ut-MRT2-Sag-1', 'Ut-MRT2-Sag-1'] 
                        "Uterus": [r"uterus.*", "ut.*"], 
                    },
                    handling_strategy=strategy,
                    ignore_case=True,  # important for matching lowercase labels
                )
                try:
                    mask_image, mapping = rtstruct.get_label_mask(
                        reference_image=ref_image,
                        roi_matcher=matcher,
                        continuous=False,
                    )
                except MissingROIError:
                    failures.append(
                        (
                            row["folder"],
                            row["SeriesInstanceUID"],
                            strategy,
                            "Missing ROI",
                            rtstruct.roi_names,
                        )
                    )
                    continue
                except Exception as e:
                    logger.error(
                        f"Failed to get label mask for {row['folder']}",
                        error=e,
                    )
                    failures.append(
                        (
                            row["folder"],
                            row["SeriesInstanceUID"],
                            strategy,
                            str(e),
                            rtstruct.roi_names,
                        )
                    )
                    raise
                    continue

                results.append(
                    (
                        mask_image,
                        mapping,
                        strategy,
                        ref_image,
                    )
                )

# p = Path("data/HNSCC/HNSCC-01-0176/RTSTRUCT_Series72843515/00000001.dcm")
#     p = Path("data/HNSCC/HNSCC-01-0176/RTSTRUCT_Series72843515/00000001.dcm")

#     # Read entire file
#     rtstruct = RTStructureSet.from_dicom(p)
#     print(rtstruct.summary())

# print(f"{rtstruct.match_roi(".*TV.*", ignore_case=True)=}")


# class ContourGeometricType(str, Enum):
#     """
#     https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.8.8.6.html
#     POINT: single point
#     OPEN_PLANAR: open contour containing coplanar points
#     OPEN_NONPLANAR: open contour containing non-coplanar points????
#     CLOSED_PLANAR: closed contour (polygon) containing coplanar points
#     """

#     POINT = "POINT"
#     OPEN_PLANAR = "OPEN_PLANAR"
#     OPEN_NONPLANAR = "OPEN_NONPLANAR"
#     CLOSED_PLANAR = "CLOSED_PLANAR"

#     def __str__(self) -> str:
#         return self.value


# class ContourSlice(np.ndarray):
#     """Represents the contour points for a single slice.
#     Simply a NumPy array with shape (n_points, 3) where the last dimension
#     represents the x, y, and z coordinates of each point.
#     Examples
#     --------
#     So if the slice has points representing a square in the x-y plane, the
#     array would look like this:
#     ```python
#     >>> ContourSlice(
#             [
#                 [0, 0, 0],
#                 [1, 0, 0],
#                 [1, 1, 0],
#                 [0, 1, 0],
#                 [0, 0, 0],
#             ]
#         )
#     ```
#     """

#     def __new__(cls, input_array: np.ndarray) -> ContourSlice:
#         obj = np.asarray(input_array).view(cls)
#         return obj

#     def __array_finalize__(self, obj: np.ndarray | None) -> None:
#         if obj is None:
#             return
#         assert self.ndim == 2
#         assert self.shape[1] == 3

#     def __array_wrap__(
#         self,
#         out_arr: np.ndarray,
#         context: tuple[np.ufunc, tuple[Any, ...], int] | None = None,  # noqa
#         subok: bool = True,
#     ) -> np.ndarray | ContourSlice:
#         """Ensure output retains ContourSlice type if shape is valid.
#         When performing operations on a ContourSlice, the output shape could be
#         altered. This method ensures that the output retains the ContourSlice type
#         if the shape is still valid.
#         Examples
#         --------
#         ```python
#         >>> contour = ContourSlice([[0, 0, 0], [1, 1, 1]])
#         >>> contour + 1
#         ContourSlice<points.shape=(2, 3)>
#         ```
#         ```python
#         >>> contour = ContourSlice([[0, 0, 0], [1, 1, 1]])
#         >>> contour.mean(axis=0)
#         array([0.5, 0.5, 0.5])
#         ```
#         """
#         if out_arr.ndim == 2 and out_arr.shape[1] == 3:
#             return out_arr.view(ContourSlice)  # Preserve type
#         # Return as NumPy array if shape changes # Return as a NumPy array if shape is altered
#         return out_arr

#     def __repr__(self) -> str:
#         return f"ContourSlice<points.shape={self.shape}>"
