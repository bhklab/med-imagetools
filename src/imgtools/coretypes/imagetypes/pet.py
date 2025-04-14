from __future__ import annotations

import pathlib
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

import SimpleITK as sitk
from pydicom import dcmread

from imgtools.coretypes import MedImage
from imgtools.io.readers import read_dicom_series
from imgtools.loggers import logger

if TYPE_CHECKING:
    from pydicom.dataset import FileDataset

__all__ = ["PET", "PETImageType"]


# alternative to StrEnum for python 3.10 compatibility
class PETImageType(str, Enum):
    """
    Enumeration for PET image types used in DICOM processing.

    This enumeration defines the two primary types of PET image representations:
    - `SUV` (Standardized Uptake Value): Represents pixel values as SUV,
      calculated using the formula:
      `SUV = Activity Concentration / (Injected Dose Quantity / Body Weight)`.
    - `ACT` (Activity Concentration): Represents pixel values as raw
      activity concentrations.

    Attributes
    ----------
    SUV : str
        Indicates the SUV image type.
    ACT : str
        Indicates the activity concentration image type.

    Examples
    --------
    >>> image_type = PETImageType.SUV  # SUV image type
    >>> print(image_type)
    'SUV'
    >>> isinstance(image_type, str)
    True
    >>> repr(PetImageType("SUV"))
    <PETImageType.SUV: 'SUV'>
    """

    SUV = "SUV"
    ACT = "ACT"


def read_dicom_pet(
    path: str,
    series_id: str | None = None,
    recursive: bool = False,
    file_names: list[str] | None = None,
    **kwargs: Any,  # noqa
) -> PET:
    return PET.from_dicom(
        path,
        series_id=series_id,
        recursive=recursive,
        file_names=file_names,
        pet_image_type=PETImageType.SUV,
        **kwargs,
    )


@dataclass
class PET(MedImage):
    metadata: Dict[str, str]

    def __init__(self, image: sitk.Image, metadata: Dict[str, str]) -> None:
        super().__init__(image)
        self.metadata = metadata

    @classmethod
    def from_dicom(
        cls,
        path: str,
        series_id: Optional[str] = None,
        recursive: bool = False,
        file_names: Optional[list[str]] = None,
        pet_image_type: PETImageType = PETImageType.SUV,
        **kwargs: Any,  # noqa
    ) -> PET:
        """Read the PET scan and returns the data frame and the image dosage in SITK format

        There are two types of existing formats which has to be mentioned in the type
        type:
            SUV: gets the image with each pixel value having SUV value
            ACT: gets the image with each pixel value having activity concentration
        SUV = Activity concenteration/(Injected dose quantity/Body weight)

        Please refer to the pseudocode: https://qibawiki.rsna.org/index.php/Standardized_Uptake_Value_(SUV)
        If there is no data on SUV/ACT then backup calculation is done based on the formula in the documentation, although, it may
        have some error.
        """
        # TODO: this logic might repetitive... idk how pet is supposed to be used
        image, metadata = read_dicom_series(
            path,
            series_id=series_id,
            recursive=recursive,
            file_names=file_names,
            **kwargs,
        )
        pet = cls(image, metadata=metadata)

        img_pet: sitk.Image = sitk.Cast(pet, sitk.sitkFloat32)
        directory_path = pathlib.Path(path)

        try:
            first_file = next(directory_path.iterdir()).as_posix()
        except StopIteration as e:
            msg = f"No files found in directory: {path}"
            raise FileNotFoundError(msg) from e

        dcm: FileDataset = dcmread(first_file)

        pet_type: PETImageType = PETImageType(pet_image_type)

        # Finding the Scale factor
        try:
            if pet_type == PETImageType.SUV:
                factor: float = dcm.to_json_dict()["70531000"]["Value"][0]
            else:
                factor = dcm.to_json_dict()["70531009"]["Value"][0]
        except KeyError:
            logger.warning(
                "Scale factor not available in DICOMs. Calculating based on metadata, may contain errors"
            )
            # factor = cls.calc_factor(dcm, pet_type)
            factor = 1.0  # fallback to 1.0 or re-enable the calc_factor logic

        # SimpleITK reads some pixel values as negative but with correct value
        img_pet = sitk.Abs(img_pet * factor)

        # metadata: Dict[str, Union[str, float, bool]] = cls.get_metadata(dcm)
        # metadata["factor"] = factor

        return cls(img_pet, metadata=metadata)

    # @staticmethod
    # def get_metadata(dcm: FileDataset) -> Dict[str, Union[str, float, bool]]:
    #     # Developer note: This method does similar work to the below `calc_factor` method.
    #     # we can extract the common code to a separate method and call it in both places.
    #     metadata = {}
    #     with contextlib.suppress(Exception):
    #         metadata["weight"] = float(dcm.PatientWeight)
    #     try:
    #         metadata["scan_time"] = datetime.datetime.strptime(
    #             dcm.AcquisitionTime, "%H%M%S.%f"
    #         )
    #         metadata["injection_time"] = datetime.datetime.strptime(
    #             dcm.RadiopharmaceuticalInformationSequence[
    #                 0
    #             ].RadiopharmaceuticalStartTime,
    #             "%H%M%S.%f",
    #         )
    #         metadata["half_life"] = float(
    #             dcm.RadiopharmaceuticalInformationSequence[
    #                 0
    #             ].RadionuclideHalfLife
    #         )
    #         metadata["injected_dose"] = float(
    #             dcm.RadiopharmaceuticalInformationSequence[
    #                 0
    #             ].RadionuclideTotalDose
    #         )
    #     except KeyError:
    #         pass

    #     return metadata

    # @staticmethod
    # def calc_factor(dcm: FileDataset, pet_image_type: str) -> float:
    #     try:
    #         weight: float = float(dcm.PatientWeight) * 1_000
    #     except KeyError:
    #         logger.warning("Patient Weight Not Present. Taking 75Kg")
    #         weight = 75_000
    #     try:
    #         scan_time: datetime.datetime = datetime.datetime.strptime(
    #             dcm.AcquisitionTime, "%H%M%S.%f"
    #         )
    #         injection_time: datetime.datetime = datetime.datetime.strptime(
    #             dcm.RadiopharmaceuticalInformationSequence[
    #                 0
    #             ].RadiopharmaceuticalStartTime,
    #             "%H%M%S.%f",
    #         )
    #         half_life: float = float(
    #             dcm.RadiopharmaceuticalInformationSequence[
    #                 0
    #             ].RadionuclideHalfLife
    #         )
    #         injected_dose: float = float(
    #             dcm.RadiopharmaceuticalInformationSequence[
    #                 0
    #             ].RadionuclideTotalDose
    #         )

    #         a: float = np.exp(
    #             -np.log(2) * ((scan_time - injection_time).seconds / half_life)
    #         )

    #         injected_dose_decay: float = a * injected_dose
    #     except Exception:
    #         logger.warning("Not enough data available, taking average values")
    #         a = np.exp(-np.log(2) * (1.75 * 3600) / 6588)
    #         injected_dose_decay = 420000000 * a

    #     suv: float = weight / injected_dose_decay
    #     if pet_image_type == "SUV":
    #         return suv
    #     else:
    #         return 1 / a
