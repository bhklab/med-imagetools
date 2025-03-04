from collections import defaultdict
from typing import Dict, List
from pathlib import Path
import json

from imgtools.logging import logger

from imgtools.io import *
from imgtools.ops import StructureSetToSegmentation

from imgtools.modules.scan import Scan
from imgtools.modules.pet import PET
from imgtools.modules.dose import Dose
from imgtools.modules.segmentation import Segmentation

class SampleLoader():
    def __init__(
            self,
            dir_path: str,
            crawl_path: str | None = '.imgtools/crawl.json',
            roi_names: Dict[str, str] | None = None,
            multiple_subseries_setting_toggle: bool = False,
        ) -> None:
        self.dir_path = dir_path
        self.roi_names = roi_names
        self.multiple_subseries_setting_toggle = multiple_subseries_setting_toggle

        with open((Path(dir_path) / crawl_path), 'r') as f:
            self.crawl_info = json.load(f)      

    def _reader(self, series_uid: str) -> auto_dicom_result:
        series_info = self.crawl_info[series_uid]
        subseries_uids = list(series_info.keys())
        
        if len(subseries_uids) > 1:
            logger.warning(f"Found >1 subseries, reading first one")

        file_names = [
            file_name for _, file_name in series_info[subseries_uids[0]]['instances'].items()
        ]

        return read_dicom_auto(
            self.dir_path, 
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

            images.append(read_dicom_auto(
                self.dir_path, 
                series_uid, 
                file_names
            ))
        
        return images
    
    def _reader_RTSTRUCT(self, series_uid: str, reference_image: Scan) -> Segmentation:
        """Convert RTSTRUCT series to Segmentation using the reference image."""
        rtstruct_to_segmentation = StructureSetToSegmentation(self.roi_names, continuous=False)
        struct = self._reader(series_uid)
        return rtstruct_to_segmentation(struct, reference_image=reference_image, **kwargs)

    def _sort_sample(self, sample: List[Dict[str, str]]) -> Dict[str, List[str]]:
        """
        Sorts the sample into a dictionary with modalities as keys and lists of series UIDs as values.

        Args:
            sample (List[Dict[str, str]]): List of dictionaries containing image metadata.

        Returns:
            Dict[str, List[str]]: Dictionary with modalities as keys and lists of series UIDs as values.
        """
        sorted_images: Dict[str, List[str]] = defaultdict(list)
        
        for image in sample:
            modality = image['modality']
            sorted_images[modality].append(image['series_uid'])

        return sorted_images
    
    def _load_reference(self, sorted_sample: Dict[str, List[str]]) -> Scan:
        """
        Load the reference scan from the sorted sample.

        This method selects the first CT or MR series from the sorted sample
        to use as the reference scan. If both CT and MR series are present,
        CT is preferred. If multiple series of the selected modality are found,
        a warning is logged and the first series is used.
        """

        modality = 'CT' if 'CT' in sorted_sample else 'MR' if 'MR' in sorted_sample else None
        if not modality:
            raise ValueError("No CT or MR series found to use as reference.")

        if len(sorted_sample[modality]) > 1:
            logger.warning(f"Found >1 {modality} series, using the first one")

        series_uid = sorted_sample.pop(modality)[0]
        return self._reader(series_uid)

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
            sorted_sample = self._sort_sample(sample)     

            # Load reference image
            reference_image = self._load_reference(sorted_sample)
            loaded_images.append(reference_image)

            # Load remaining images
            for modality, series_uids in sorted_sample.items():
                if modality == 'RTSTRUCT':
                    for series_uid in series_uids:
                        loaded_images.append(self._reader_RTSTRUCT(series_uid, reference_image))
                else:
                    for series_uid in series_uids:
                        loaded_images.append(self._reader(series_uid))
            
            return loaded_images