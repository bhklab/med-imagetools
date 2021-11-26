import pydicom
from matplotlib import pyplot as plt
import os
import numpy as np
import SimpleITK as sitk
import warnings
import datetime

def read_image(path):
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(path)
    reader.SetFileNames(dicom_names)
    reader.MetaDataDictionaryArrayUpdateOn()
    reader.LoadPrivateTagsOn()

    return reader.Execute()

class Petscan(sitk.Image):
    def __init__(self,ptscan,df):
        super().__init__(ptscan)
        self.ptscan = ptscan
        self.df = df
    
    @classmethod
    def get_from_pt(cls,path,type="SUV"):
        '''
        Reads the PET scan and returns the data frame and the image dosage in SITK format
        There are two types of existing formats which has to be mentioned in the type
        type:
            SUV: gets the image with each pixel value having SUV value
            ACT: gets the image with each pixel value having activity concenteration
        SUV = Activity concenteration/(Injected dose quantity/Body weight)

        Please refer to the pseudocode: https://qibawiki.rsna.org/index.php/Standardized_Uptake_Value_(SUV) 
        If there is no data on SUV/ACT then backup calculation is done based on the formula in the documentatuib, although, it may
        have some error.
        '''
        PET=read_image(path)
        path_one = os.path.join(path,os.listdir(path)[0])
        df = pydicom.dcmread(path_one)
        try:
            if type=="SUV":
                factor = df.to_json_dict()['70531000']["Value"][0]
            else:
                factor = df.to_json_dict()['70531009']['Value'][0]
        except:
            warnings.warn("Scale factor not available in DICOMs. Calculating based on metadata, may contain errors")
            factor = cls.calc_factor(df,type)
        ptscan = sitk.Cast(PET, sitk.sitkFloat32)
        #Sometimes the pixel values are negetive but with correct value
        ptscan = sitk.Abs(ptscan * factor)
        return cls(ptscan,df)
        
    def get_metadata(self):
        '''
        Forms the important metadata for reference in the dictionary format
        {
            AcquisitionTime
            PatientWeight
            SliceThickness
            PixelSpacing
            InjectionTime RadiopharmaceuticalInformationSequence[0].RadiopharmaceuticalStartTime
            totaldose RadiopharmaceuticalInformationSequence[0].RadionuclideTotalDose
            halflife RadiopharmaceuticalInformationSequence[0].RadionuclideHalfLife
        }
        '''
        self.metadata = {}
        #In kg
        self.metadata["weight"] = float(self.df.PatientWeight)
        #In seconds
        self.metadata["scan_time"] = float(self.df.AcquisitionTime)/1000
        self.metadata["injection_time"] = float(self.df.RadiopharmaceuticalInformationSequence[0].RadiopharmaceuticalStartTime)/1000
        self.metadata["half_life"] = float(self.df.RadiopharmaceuticalInformationSequence[0].RadionuclideHalfLife)
        self.metadata["injected_dose"] = float(self.df.RadiopharmaceuticalInformationSequence[0].RadionuclideTotalDose)
        
        return self.metadata

    def resample_pet(self,ct_scan:sitk.Image) -> sitk.Image:
        '''
        Resamples the PET scan so that it can be overlayed with CT scan. The beginning and end slices of the 
        resampled PET scan might be empty due to the interpolation
        '''
        resampled_pt = sitk.Resample(self.ptscan, ct_scan,interpolator=sitk.sitkNearestNeighbor)
        return resampled_pt

    def show_overlay(self,ct_scan:sitk.Image,slice_number:int):
        '''
        For a given slice number, the function resamples PET scan and overlays on top of the CT scan and returns the figure of the
        overlay
        '''
        pet_resampled = self.resample_pet(ct_scan)
        fig = plt.figure("Overlayed image",figsize=[15,10])
        pt_upsamp = sitk.GetArrayFromImage(pet_resampled)
        plt.subplot(1,3,1)
        plt.imshow(pt_upsamp[slice_number,:,:])
        plt.subplot(1,3,2)
        ct_np_img = sitk.GetArrayFromImage(ct_scan)
        plt.imshow(ct_np_img[slice_number,:,:])
        plt.subplot(1,3,3)
        plt.imshow(ct_np_img[slice_number,:,:], cmap=plt.cm.gray)
        plt.imshow(pt_upsamp[slice_number,:,:], cmap=plt.cm.hot, alpha=.4)
        return fig

    @staticmethod
    def calc_factor(df,type):
        '''
        Following the calculation formula stated in https://gist.github.com/pangyuteng/c6a075ba9aa00bb750468c30f13fc603
        '''
        # print(df)
        #Fetching some required Meta Data
        try:
            weight = float(df.PatientWeight)*1000
        except:
            warnings.warn("Patient Weight Not Present. Taking 75Kg")
            weight = 75000
        try:
            Scan_time = datetime.datetime.strptime(df.AcquisitionTime,'%H%M%S.%f')
            Injection_time = datetime.datetime.strptime(df.RadiopharmaceuticalInformationSequence[0].RadiopharmaceuticalStartTime,'%H%M%S.%f')
            half_life = float(df.RadiopharmaceuticalInformationSequence[0].RadionuclideHalfLife)
            injected_dose = float(df.RadiopharmaceuticalInformationSequence[0].RadionuclideTotalDose)

            #Calculate Activity concenteration factor
            A = np.exp(-np.log(2)*((Scan_time-Injection_time).seconds/half_life))

            #Calculate SUV factor
            injected_dose_decay = A*injected_dose
        except:
            warnings.warn("Not enough data available, taking average values")
            A = np.exp(-np.log(2)*(1.75*3600)/6588); # 90 min waiting time, 15 min preparation
            injected_dose_decay = 420000000 * A; # 420 MBq

        SUV = weight/injected_dose_decay
        if type=="SUV":
            return SUV
        else:
            return 1/A