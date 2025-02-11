import SimpleITK as sitk
from rt_utils import RTStructBuilder
import logging
import numpy as np
import os

'''You need to install rt_utils first using 
    pip install rt_utils'''


def segmentations_to_dicom(save_path:str,orig_series_info:dict, segmentation:sitk.Image,segmentations_labels:dict,
                             color_list=None, rtstruct_basefilename='rtstruct.dcm'):
    """
    This function takes a list of the original dicom data, moves it to the save_path and creates a corresponding rt_struct
    @param image_set_name: name of the image set used to create the dicom sub directory
    @param save_path: directory to save dicom data
    @param orig_series_info: original series info see @get_dicom_series_dict_pyd
    @param segmentation: the image containing integer segmentation data
    @param segmentations_labels: a dictionary with segmentation label information mapping ints in @segmentation to label
    name e.g. {1: 'Bladder', 2: 'Rectum', 3: 'Sigmoid', 4: 'SmallBowel'}
    @return:
    """
    _logger=logging.getLogger(__name__)
    #make output dir
    if not os.path.isdir(save_path):
        _logger.warning(f'Making path: {save_path}')
        os.makedirs(save_path)


    im_array = sitk.GetArrayFromImage(segmentation)
    rtstruct = RTStructBuilder.create_new(dicom_series_path=orig_series_info)
    for i,(key,name) in enumerate(segmentations_labels.items()):
        mask = np.where(im_array!=key,0,im_array)
        mask = np.array(mask,dtype=bool)
        mask = np.transpose(mask, (1,2,0))

        index = i%len(color_list)

        rtstruct.add_roi(mask=mask, name=name, color=color_list[index],approximate_contours=False)


    rtstruct_name = os.path.join(save_path,rtstruct_basefilename)
    _logger.info(f'Saving rtstruct data: {rtstruct_name}')
    rtstruct.save(rtstruct_name)
