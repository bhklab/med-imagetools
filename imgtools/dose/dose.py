import pydicom
from matplotlib import pyplot as plt
import os
import numpy as np
import SimpleITK as sitk
import warnings


def read_image(path):
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(path)
    reader.SetFileNames(dicom_names)
    reader.MetaDataDictionaryArrayUpdateOn()
    reader.LoadPrivateTagsOn()

    return reader.Execute()


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
        DOSE = read_image(path)[:,:,:,0]
        #Get the metadata
        dcm_path = os.path.join(path,os.listdir(path)[0])
        df = pydicom.dcmread(dcm_path)
        #Convert to SUV
        factor = float(df.DoseGridScaling)
        img_dose = sitk.Cast(DOSE, sitk.sitkFloat32)
        img_dose = img_dose * factor
        return cls(img_dose,df)

    def resample_rt(self,ct_scan:sitk.Image) -> sitk.Image:
        '''
        Resamples the RTDOSE information so that it can be overlayed with CT scan. The beginning and end slices of the 
        resampled RTDOSE scan might be empty due to the interpolation
        '''
        resampled_pt = sitk.Resample(self.img_dose, ct_scan,interpolator=sitk.sitkNearestNeighbor)
        return resampled_pt

    def show_overlay(self,ct_scan:sitk.Image,slice_number:int):
        '''
        For a given slice number, the function resamples RTDOSE scan and overlays on top of the CT scan and returns the figure of the
        overlay
        '''
        dose_resampled = self.resample_rt(ct_scan)
        fig = plt.figure("Overlayed RTdose image",figsize=[15,10])
        ds_upsamp = sitk.GetArrayFromImage(dose_resampled)
        plt.subplot(1,3,1)
        plt.imshow(ds_upsamp[slice_number,:,:])
        plt.subplot(1,3,2)
        ct_np_img = sitk.GetArrayFromImage(ct_scan)
        plt.imshow(ct_np_img[slice_number,:,:])
        plt.subplot(1,3,3)
        plt.imshow(ct_np_img[slice_number,:,:], cmap=plt.cm.gray)
        plt.imshow(ds_upsamp[slice_number,:,:], cmap=plt.cm.hot, alpha=.4)
        return fig
        
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
        try:
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
        except:
            warnings.warn("No DVH information present in the DICOM. Returning None")
            self.meta_dvh = None
            
        return self.meta_dvh

    

