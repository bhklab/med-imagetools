from imgtools.io import Dataset
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
import torchio as tio
import os
from torch.utils.data import DataLoader
from typing import List
import re

class select_roi_names(tio.LabelTransform):
    """
    Based on the given roi names, selects from the given set
    """
    def __init__(
            self,
            roi_names: List[str] = None,
            **kwargs
            ) -> None:
        super().__init__(**kwargs)
        self.kwargs = kwargs
        self.roi_names = roi_names
    
    def apply_transform(self,subject):
        #list of roi_names
        metadata = subject["metadata_RTSTRUCT_CT"]
        for image in self.get_images(subject):
            patterns = self.roi_names
            mask = torch.empty_like(image.data)[:len(patterns)]
            for j,pat in enumerate(patterns):
                k = []
                for i,col in enumerate(metadata):
                    if re.match(pat,col,flags=re.IGNORECASE):
                        k.append(i)
                        print(col)
                mask[j] = (image.data[k].sum(axis=0)>0)*1    
            image.set_data(mask)
        return subject
    
    def is_invertible(self):
        return False


#Data directory
output_directory = "/cluster/projects/radiomics/Temp/vishwesh/demo_data"
transforms = tio.Compose([
    tio.ToCanonical(),
    tio.Resample(4),
    tio.CropOrPad((96,96,40))],
    select_roi_names(["^Body$"]),
    tio.RandomFlip(),
    tio.OneHot())
subjects_dataset = Dataset.load_from_nrrd(output_directory,transform=transforms,ignore_multi=True)
training_loader = DataLoader(subjects_dataset, batch_size=4)

