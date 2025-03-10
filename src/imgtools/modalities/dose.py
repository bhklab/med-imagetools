from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Union

import numpy as np
import SimpleITK as sitk
from pydicom import Dataset, dcmread

from imgtools.logging import logger
from imgtools.modalities.utils import read_image


"""
TODO:: Move metadata extraction to on load
"""
__all__ = ["Dose"]


@dataclass
class Dose(sitk.Image):
    img_dose: sitk.Image
    dcm: Dataset
    metadata: Dict[str, str] | None = None

    @classmethod
    def from_dicom(cls, path: str) -> Dose:
        """
        Reads the data and returns the data frame and the image dosage in SITK format
        """
        dose = sitk.ReadImage(path) if ".dcm" in path else read_image(path)

        # if 4D, make 3D
        if dose.GetDimension() == 4:
            dose = dose[:, :, :, 0]

        # Get the metadata
        df = dcmread(path)

        # Convert to SUV
        factor = float(df.DoseGridScaling)
        img_dose = sitk.Cast(dose, sitk.sitkFloat32)
        img_dose = img_dose * factor

        metadata: Dict[str, str] = {}

        return cls(img_dose, df, metadata)

    def get_metadata(
        self,
    ) -> Dict[
        Union[str, int], Union[str, float, Dict[str, Union[str, float, list]]]
    ]:
        """
        dict[str | int, str | float | dict[str, str | float | list]]:


        Forms Dose-Value Histogram (DVH) from DICOM metadata
        {
            dvh_type
            dose_type
            dose_units
            vol_units
            ROI_ID: {
                vol: different volume values for different dosage bins
                dose_bins: different dose bins
                max_dose: max dose value
                mean_dose : mean dose value
                min_dose: min dose value
                total_vol: total volume of the ROI
            }
        }
        """
        try:
            num_roi = len(self.dcm.DVHSequence)
            self.dvh = {}
            # These properties are uniform across all the ROIs
            self.dvh["dvh_type"] = self.dcm.DVHSequence[0].DVHType
            self.dvh["dose_units"] = self.dcm.DVHSequence[0].DoseUnits
            self.dvh["dose_type"] = self.dcm.DVHSequence[0].DoseType
            self.dvh["vol_units"] = self.dcm.DVHSequence[0].DVHVolumeUnits
            # ROI specific properties
            for i in range(num_roi):
                raw_data = np.array(self.dcm.DVHSequence[i].DVHData)
                n = len(raw_data)

                # ROI ID
                roi_reference = (
                    self.dcm.DVHSequence[i]
                    .DVHReferencedROISequence[0]
                    .ReferencedROINumber
                )

                # Make dictionary for each ROI ID
                self.dvh[roi_reference] = {}

                # DVH specifc properties
                doses_bin = np.cumsum(raw_data[0:n:2])
                vol = raw_data[1:n:2]
                self.dvh[roi_reference]["dose_bins"] = doses_bin.tolist()
                self.dvh[roi_reference]["vol"] = vol.tolist()

                # ROI specific properties
                tot_vol = np.sum(vol)
                non_zero_index = np.where(vol != 0)[0]
                min_dose = doses_bin[non_zero_index[0]]
                max_dose = doses_bin[non_zero_index[-1]]
                mean_dose = np.sum(doses_bin * (vol / np.sum(vol)))
                self.dvh[roi_reference]["max_dose"] = max_dose
                self.dvh[roi_reference]["mean_dose"] = mean_dose
                self.dvh[roi_reference]["min_dose"] = min_dose
                self.dvh[roi_reference]["total_vol"] = tot_vol
        except AttributeError:
            logger.warning(
                "No DVH information present in the DICOM. Returning empty dictionary"
            )
            self.dvh = {}

        return self.dvh  # type: ignore
