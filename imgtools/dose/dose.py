import pydicom
from matplotlib import pyplot as plt
import os
import numpy as np
import SimpleITK as sitk

class Dose(sitk.Image):
    def __init__(self,img_dose,df):
        super().__init__(img_dose)
        self.img_dose = img_dose
        self.df = df
        
    @classmethod
    def get_from_rtdose(cls,path):
        '''
        Reads the data and returns the data frame and the image dosage in SITK format
        '''
        df = pydicom.dcmread(path)
        img = df.pixel_array
        #Dosage values in each pixel
        img_dose = sitk.GetImageFromArray(float(df.DoseGridScaling)*img)
        return cls(img_dose,df)

    def form_DVH(self):
        '''
        Forms the Dose-Value Histogram metadata in the dictionary format
        {
            dvhtype:
            dosetype:
            dose_units:
            vol_units:
            ROI_ID: {
                vol: different volume values for different dosage bins
                dose_bins: different dose bins
                max_dose: max dose value
                mean_dose : mean dose value
                min_dose: min dose value
                total_vol: total volume of the ROI
            }
        }
        '''
        n_ROI =  len(self.df.DVHSequence)
        self.meta_dvh = {}
        #These properties are uniform across all the ROIs
        self.meta_dvh["dvhtype"] = self.df.DVHSequence[0].DVHType   
        self.meta_dvh["dose_units"] = self.df.DVHSequence[0].DoseUnits
        self.meta_dvh["dosetype"] = self.df.DVHSequence[0].DoseType
        self.meta_dvh["vol_units"] = self.df.DVHSequence[0].DVHVolumeUnits
        #ROI specific properties
        for i in range(n_ROI):
            raw_data = np.array(self.df.DVHSequence[i].DVHData)
            n = len(raw_data)
            #ROI ID
            ROI_reference = self.df.DVHSequence[i].DVHReferencedROISequence[0].ReferencedROINumber
            # Make dictionary for each ROI ID
            self.meta_dvh[ROI_reference] = {}
            # DVH specifc properties
            doses_bin = np.cumsum(raw_data[0:n:2])
            vol = raw_data[1:n:2]
            self.meta_dvh[ROI_reference]["dose_bins"] = doses_bin
            self.meta_dvh[ROI_reference]["vol"] = vol
            # ROI specific properties
            tot_vol = np.sum(vol)
            dosevol_array = np.multiply(doses_bin,vol)
            non_zero_index =  np.where(vol!=0)[0]
            min_dose = doses_bin[non_zero_index[0]]
            max_dose = doses_bin[non_zero_index[-1]]
            mean_dose = np.sum(doses_bin*(vol/np.sum(vol)))
            self.meta_dvh[ROI_reference]["max_dose"] = max_dose
            self.meta_dvh[ROI_reference]["mean_dose"] = mean_dose
            self.meta_dvh[ROI_reference]["min_dose"] = min_dose
            self.meta_dvh[ROI_reference]["total_vol"] = tot_vol

        return self.meta_dvh

    

