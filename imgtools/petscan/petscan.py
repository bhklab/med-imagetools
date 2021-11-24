import pydicom
from matplotlib import pyplot as plt
import os
import numpy as np
import SimpleITK as sitk
import warnings

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
        DF = []
        IMG = []
        file_names = np.sort(os.listdir(path))
        for file_paths in file_names:
            path_full = os.path.join(path,file_paths)
            df = pydicom.dcmread(path_full)
            img = df.pixel_array
            try:
                if type=="SUV":
                    factor = df.to_json_dict()['70531000']["Value"][0]
                else:
                    factor = df.to_json_dict()['70531009']['Value'][0]
            except:
                warnings.warn("Warning... Scale factor not available in DICOMs. Calculating based on metadata, may contain errors")
                factor = cls.calc_factor(df,type)
            IMG.append(img*factor)
            DF.append(df)
        all_img = np.array(IMG).transpose((0,2,1))
        ptscan = sitk.GetImageFromArray(all_img)
        return cls(ptscan,DF)
        
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
        self.metadata["weight"] = float(self.df[0].PatientWeight)
        #In seconds
        self.metadata["scan_time"] = float(self.df[0].AcquisitionTime)/1000
        self.metadata["injection_time"] = float(self.df[0].RadiopharmaceuticalInformationSequence[0].RadiopharmaceuticalStartTime)/1000
        self.metadata["half_life"] = float(self.df[0].RadiopharmaceuticalInformationSequence[0].RadionuclideHalfLife)
        self.metadata["injected_dose"] = float(self.df[0].RadiopharmaceuticalInformationSequence[0].RadionuclideTotalDose)
        
        return self.metadata

    @staticmethod
    def calc_factor(df,type):
        '''
        Following the calculation formula stated in https://gist.github.com/pangyuteng/c6a075ba9aa00bb750468c30f13fc603
        '''
        #Fetching some required Meta Data
        weight = float(df.PatientWeight)*1000
        Scan_time = float(df.AcquisitionTime)/1000
        Injection_time = float(df.RadiopharmaceuticalInformationSequence[0].RadiopharmaceuticalStartTime)/1000
        half_life = float(df.RadiopharmaceuticalInformationSequence[0].RadionuclideHalfLife)
        injected_dose = float(df.RadiopharmaceuticalInformationSequence[0].RadionuclideTotalDose)

        #Calculate Activity concenteration factor
        A = np.exp(-np.log(2)*((Scan_time-Injection_time)/half_life))

        #Calculate SUV factor
        SUV = A/(injected_dose/weight)

        if type=="SUV":
            return SUV
        else:
            return A