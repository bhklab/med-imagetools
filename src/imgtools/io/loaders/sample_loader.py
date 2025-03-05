import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from imgtools.io import auto_dicom_result, read_dicom_auto
from imgtools.logging import logger
from imgtools.modalities import PET, Dose, Scan, Segmentation


class SampleLoader:
    def __init__(
        self,
        crawl_path: str,
        multiple_subseries_setting_toggle: bool = False,
        roi_names: Dict[str, str] | None = None,
        existing_roi_indices: Dict[str, int] | None = None,
        ignore_missing_regex: bool = False,
        roi_select_first: bool = False,
        roi_separate: bool = False,
    ) -> None:
        self.multiple_subseries_setting_toggle = (
            multiple_subseries_setting_toggle
        )

        self.roi_names = roi_names
        self.existing_roi_indices = existing_roi_indices
        self.ignore_missing_regex = ignore_missing_regex
        self.roi_select_first = roi_select_first
        self.roi_separate = roi_separate

        with open((crawl_path), "r") as f:
            self.crawl_info = json.load(f)

    def _reader(
        self, series_uid: str, load_subseries: bool = False
    ) -> auto_dicom_result | List[auto_dicom_result]:
        """
        Reads DICOM files for a given series UID.

        Parameters
        ----------
        series_uid : str
            The series UID to read.
        load_subseries : bool, optional
            Whether to load multiple subseries, by default False.

        Returns
        -------
        auto_dicom_result | List[auto_dicom_result]
            The loaded DICOM data or a list of loaded DICOM data for each subseries.
        """
        series_info = self.crawl_info[series_uid]
        subseries_uids = list(series_info.keys())

        if load_subseries:
            images = []
            for subseries_uid in subseries_uids:
                folder = series_info[subseries_uid]["folder"]
                file_names = [
                    (Path(folder) / file_name).as_posix()
                    for file_name in series_info[subseries_uid][
                        "instances"
                    ].values()
                ]

                images.append(read_dicom_auto(folder, series_uid, file_names))

            return images
        else:
            if len(subseries_uids) > 1:
                logger.warning(
                    "Found >1 subseries, combining them into one image"
                )

            folder = series_info[subseries_uids[0]]["folder"]
            file_names = []
            for subseries_uid in subseries_uids:
                file_names += [
                    (Path(folder) / file_name).as_posix()
                    for file_name in series_info[subseries_uid][
                        "instances"
                    ].values()
                ]

            return read_dicom_auto(folder, series_uid, file_names)

    def _group_by_modality(
        self, sample: List[Dict[str, str]]
    ) -> Dict[str, List[str]]:
        """
        Groups the sample into a dictionary with modalities as keys and lists of series UIDs as values.

        Args:
            sample (List[Dict[str, str]]): List of dictionaries containing image metadata.

        Returns:
            Dict[str, List[str]]: Dictionary with modalities as keys and lists of series UIDs as values.
        """
        grouped_images: Dict[str, List[str]] = defaultdict(list)

        for image in sample:
            modality = image["Modality"]
            grouped_images[modality].append(image["Series"])

        return grouped_images

    def load(
        self, sample: List[Dict[str, str]]
    ) -> List[Scan | PET | Dose | Segmentation]:
        """
        Load and process medical imaging data from a given sample.
        Parameters
        ----------
        sample : List[Dict[str, str]]
            A list of dictionaries where each dictionary contains information about a specific imaging series.
            The keys in the dictionary represent the modality (e.g., 'CT', 'MR', 'RTSTRUCT') and the values are the series UIDs.
            Example sample: [{'CT': '1.2.3'}, {'RTSTRUCT': '1.2.3.4'}, {'RTSTRUCT': '1.2.3.5'},]
        Returns
        -------
        List[Scan | PET | Dose | Segmentation]
            A list of loaded imaging objects, which can be of types Scan, PET, Dose, or Segmentation.
        Notes
        -----
        - If no 'CT' series is found, the first 'MR' series will be used as the reference image.
        - If multiple 'CT' or 'MR' series are found, a warning will be logged and the first series will be used.
        """
        loaded_images: List[Scan | PET | Dose | Segmentation] = []

        if (
            len(sample) == 1 and self.multiple_subseries_setting_toggle
        ):  # EDGE CASE
            return self._reader(sample[0]["series_uid"], load_subseries=True)
        else:
            grouped_images = self._group_by_modality(sample)

            # Load reference image
            reference_modality = (
                "CT"
                if "CT" in grouped_images
                else "MR"
                if "MR" in grouped_images
                else None
            )
            if not reference_modality:
                raise ValueError(
                    "No CT or MR series found to use as reference."
                )
            if len(grouped_images[reference_modality]) > 1:
                msg = f"Found >1 {reference_modality} series, using the first one"
                raise ValueError(msg)

            series_uid = grouped_images.pop(reference_modality)[0]
            reference_image = self._reader(series_uid)
            loaded_images.append(reference_image)

            # Load remaining images
            for modality, series_uids in grouped_images.items():
                for series_uid in series_uids:
                    image = self._reader(series_uid)
                    if modality == "RTSTRUCT":
                        image = image.to_segmentation(
                            reference_image,
                            self.roi_names,
                            continuous=False,
                            existing_roi_indices=self.existing_roi_indices,
                            ignore_missing_regex=self.ignore_missing_regex,
                            roi_select_first=self.roi_select_first,
                            roi_separate=self.roi_separate,
                        )
                    loaded_images.append(image)

            return loaded_images


if __name__ == "__main__":
    from rich import print  # noqa
    from imgtools.dicom.interlacer import Interlacer

    interlacer = Interlacer(".imgtools/data/crawldb.csv")
    interlacer.visualize_forest()
    samples = interlacer.query("CT,RTSTRUCT")

    loader = SampleLoader(".imgtools/data/crawldb.json")

    for sample in samples:
        print(loader.load(sample))
