from collections import defaultdict
from typing import Dict, List
import json

from imgtools.logging import logger

from imgtools.io import read_dicom_auto, auto_dicom_result

from imgtools.modules.scan import Scan
from imgtools.modules.pet import PET
from imgtools.modules.dose import Dose
from imgtools.modules.segmentation import Segmentation

class SampleLoader():
    def __init__(
            self,
            crawl_path: str,
            roi_names: Dict[str, str] | None = None,
            multiple_subseries_setting_toggle: bool = False,
        ) -> None:
        self.roi_names = roi_names
        self.multiple_subseries_setting_toggle = multiple_subseries_setting_toggle

        with open((crawl_path), 'r') as f:
            self.crawl_info = json.load(f)      

    def _reader(self, series_uid: str) -> auto_dicom_result:
        series_info = self.crawl_info[series_uid]
        subseries_uids = list(series_info.keys())
        
        if len(subseries_uids) > 1:
            logger.warning(f"Found >1 subseries, reading first one")

        file_names = [
            file_name for _, file_name in series_info[subseries_uids[0]]['instances'].items()
        ]
        folder = series_info[subseries_uids[0]]['folder']

        return read_dicom_auto(
            folder, 
            series_uid, 
            file_names
        )
    
    def _reader_multiple(self, series_uid: str) -> List[auto_dicom_result]:
        series_info = self.crawl_info[series_uid]
        subseries_uids = list(series_info.keys())
        images = []

        for subseries_uid in subseries_uids:
            file_names = [
                file_name for _, file_name in series_info[subseries_uid]['instances'].items()
            ]
            folder = series_info[subseries_uid]['folder']

            images.append(read_dicom_auto(
                folder, 
                series_uid, 
                file_names
            ))
        
        return images

    def _group_by_modality(self, sample: List[Dict[str, str]]) -> Dict[str, List[str]]:
        """
        Groups the sample into a dictionary with modalities as keys and lists of series UIDs as values.

        Args:
            sample (List[Dict[str, str]]): List of dictionaries containing image metadata.

        Returns:
            Dict[str, List[str]]: Dictionary with modalities as keys and lists of series UIDs as values.
        """
        grouped_images: Dict[str, List[str]] = defaultdict(list)
        
        for image in sample:
            modality = image['modality']
            grouped_images[modality].append(image['series_uid'])

        return grouped_images

    def load(self, sample: List[Dict[str, str]]) -> List[Scan | PET | Dose | Segmentation]:
        """
        Load and process medical imaging data from a given sample.
        Parameters
        ----------
        sample : List[Dict[str, str]]
            A list of dictionaries where each dictionary contains information about a specific imaging series.
            The keys in the dictionary represent the modality (e.g., 'CT', 'MR', 'RTSTRUCT') and the values are the series UIDs.
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

        if len(sample) == 1 and self.multiple_subseries_setting_toggle: # EDGE CASE
            return self._reader_multiple(sample[0]['series_uid'])
        else:   
            grouped_images = self._group_by_modality(sample)     

            # Load reference image
            reference_modality = 'CT' if 'CT' in grouped_images else 'MR' if 'MR' in grouped_images else None
            if not reference_modality:
                raise ValueError("No CT or MR series found to use as reference.")

            if len(grouped_images[reference_modality]) > 1:
                logger.warning(f"Found >1 {reference_modality} series, using the first one")

            series_uid = grouped_images.pop(reference_modality)[0]
            reference_image = self._reader(series_uid)
            loaded_images.append(reference_image)

            # Load remaining images
            for modality, series_uids in grouped_images.items():
                    for series_uid in series_uids:
                        image = self._reader(series_uid)
                        if modality == 'RTSTRUCT':
                            image = image.to_segmentation(
                                reference_image, 
                                self.roi_names, 
                                continuous=False, 
                                **kwargs
                            )
                        loaded_images.append(image)
            
            return loaded_images