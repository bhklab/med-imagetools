from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import SimpleITK as sitk
from pydicom import dcmread

from imgtools.coretypes import MedImage
from imgtools.io.readers import read_dicom_series

__all__ = ["Dose"]


def read_dicom_dose(
    path: str,
    series_id: str | None = None,
    recursive: bool = False,
    file_names: list[str] | None = None,
    **kwargs: Any,  # noqa
) -> Dose:
    return Dose.from_dicom(
        path,
        series_id=series_id,
        recursive=recursive,
        file_names=file_names,
        **kwargs,
    )


@dataclass
class Dose(MedImage):
    metadata: Dict[str, str]

    def __init__(self, image: sitk.Image, metadata: Dict[str, str]) -> None:
        super().__init__(image)
        self.metadata = metadata

    @classmethod
    def from_dicom(
        cls,
        path: str,
        series_id: str | None = None,
        file_names: list[str] | None = None,
        **kwargs: Any,  # type: ignore # noqa
    ) -> Dose:
        """
        Reads the data and returns the data frame and the image dosage in SITK format
        """
        dose, metadata = read_dicom_series(
            path,
            series_id=series_id,
            file_names=file_names,
            **kwargs,
        )

        # if 4D, make 3D
        if dose.GetDimension() == 4:
            dose = dose[:, :, :, 0]

        # Get the metadata
        df = dcmread(path)

        # Convert to SUV
        factor = float(df.DoseGridScaling)
        img_dose = sitk.Cast(dose, sitk.sitkFloat32)
        img_dose = img_dose * factor

        metadata.update(
            {
                "DoseGridScaling": str(factor),
                "DoseUnits": str(df.DoseUnits),
                "DoseType": str(df.DoseType),
            }
        )

        return cls(img_dose, metadata)

    ## DEPRECATED until DVH can be handled by .metadata + indexing works
    # @staticmethod
    # def get_dvh(
    #     dcm: Dataset,
    # ) -> Dict[
    #     Union[str, int], Union[str, float, Dict[str, Union[str, float, list]]]
    # ]:
    #     """
    #     dict[str | int, str | float | dict[str, str | float | list]]:

    #     Forms Dose-Value Histogram (DVH) from DICOM metadata
    #     {
    #         dvh_type
    #         dose_type
    #         dose_units
    #         vol_units
    #         ROI_ID: {
    #             vol: different volume values for different dosage bins
    #             dose_bins: different dose bins
    #             max_dose: max dose value
    #             mean_dose : mean dose value
    #             min_dose: min dose value
    #             total_vol: total volume of the ROI
    #         }
    #     }
    #     """
    #     try:
    #         num_roi = len(dcm.DVHSequence)
    #         dvh = {}
    #         # These properties are uniform across all the ROIs
    #         dvh["dvh_type"] = dcm.DVHSequence[0].DVHType
    #         dvh["dose_units"] = dcm.DVHSequence[0].DoseUnits
    #         dvh["dose_type"] = dcm.DVHSequence[0].DoseType
    #         dvh["vol_units"] = dcm.DVHSequence[0].DVHVolumeUnits
    #         # ROI specific properties
    #         for i in range(num_roi):
    #             raw_data = np.array(dcm.DVHSequence[i].DVHData)
    #             n = len(raw_data)

    #             # ROI ID
    #             roi_reference = (
    #                 dcm.DVHSequence[i]
    #                 .DVHReferencedROISequence[0]
    #                 .ReferencedROINumber
    #             )

    #             # Make dictionary for each ROI ID
    #             dvh[roi_reference] = {}

    #             # DVH specifc properties
    #             doses_bin = np.cumsum(raw_data[0:n:2])
    #             vol = raw_data[1:n:2]
    #             dvh[roi_reference]["dose_bins"] = doses_bin.tolist()
    #             dvh[roi_reference]["vol"] = vol.tolist()

    #             # ROI specific properties
    #             tot_vol = np.sum(vol)
    #             non_zero_index = np.where(vol != 0)[0]
    #             min_dose = doses_bin[non_zero_index[0]]
    #             max_dose = doses_bin[non_zero_index[-1]]
    #             mean_dose = np.sum(doses_bin * (vol / np.sum(vol)))
    #             dvh[roi_reference]["max_dose"] = max_dose
    #             dvh[roi_reference]["mean_dose"] = mean_dose
    #             dvh[roi_reference]["min_dose"] = min_dose
    #             dvh[roi_reference]["total_vol"] = tot_vol
    #     except AttributeError:
    #         logger.warning(
    #             "No DVH information present in the DICOM. Returning empty dictionary"
    #         )
    #         dvh = {}

    #     return dvh  # type: ignore
