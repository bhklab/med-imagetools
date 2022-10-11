from genericpath import exists
import os, pathlib, ast
from typing import List, Sequence, Optional, Callable, Iterable, Dict,Tuple
from tqdm import tqdm

import SimpleITK as sitk
import torchio as tio
import pandas as pd

from imgtools.io import file_name_convention
from imgtools.ops import StructureSetToSegmentation, ImageAutoInput, Resample, BaseOp
from imgtools.pipeline import Pipeline
from joblib import Parallel, delayed

class Dataset(tio.SubjectsDataset):
    """
    This class takes in medical dataset in the form of nrrds or directly from the dataset and converts the data into torchio.Subject object, which can be loaded into 
    torchio.SubjectDataset object.
    This class inherits from torchio.SubjectDataset object, which can support transforms and torch.Dataloader.
    Read more about torchio from https://torchio.readthedocs.io/quickstart.html and torchio.SubjectDataset from https://github.com/fepegar/torchio/blob/3e07b78da16d6db4da7193325b3f9cb31fc0911a/torchio/data/dataset.py#L101
    """
    def __init__(
        self,
        subjects: Sequence[tio.Subject],
        path: str,
        ) -> List[tio.Subject]:
        super().__init__(subjects)
        self.subjects = subjects
        self.path = path
    
    @classmethod
    def load_image(
            cls,
            path:str,
            ignore_multi: bool = True,
            ) -> List[tio.Subject]:
        """
        Based on the given path, passess the processed nrrd files present in the directory and the metadata associated with it and creates a list of Subject instances
        Parameters
            path: Path to the output directory passed to the autopipeline script. The output directory should have all the user mentioned modalities processed and present in their folder. The directory
                  should additionally have dataset.csv which stores all the metadata
        """
        path_metadata = pathlib.Path(path, "dataset.csv").as_posix()
        if not os.path.exists(path_metadata):
            raise ValueError("The specified path has no file name {}".format(path_metadata))
        df_metadata = pd.read_csv(path_metadata,index_col=0)
        
        for col in df_metadata.columns:
            if col.startswith("output_folder"):
                df_metadata[col] = df_metadata[col].apply(lambda x: pathlib.Path(os.path.split(os.path.dirname(path))[0], x).as_posix() if isinstance(x, str) else x) #input folder joined with the rel path
        
        output_streams = [("_").join(cols.split("_")[2:]) for cols in df_metadata.columns if cols.split("_")[0] == "output"]
        imp_metadata = [cols for cols in df_metadata.columns if cols.split("_")[0] in ("metadata")]
        #Ignores multiple connection to single modality
        if ignore_multi:
            output_streams = [items for items in output_streams if items.split("_")[-1].isnumeric()==False]
            imp_metadata = [items for items in imp_metadata if items.split("_")[-1].isnumeric()==False]
        
        #Based on the file naming convention
        subject_id_list = list(df_metadata.index)
        subjects = []
        for subject_id in tqdm(subject_id_list):
            temp = {}
            for col in output_streams:
                metadata_name = f"metadata_{col}"
                if 'RTSTRUCT' in col:
                    # print("df in dataset")
                    # print(df_metadata.loc[subject_id])
                    filenames = ast.literal_eval(df_metadata.loc[subject_id]['metadata_RTSTRUCT_CT'])[0]
                    filename = filenames[0]
                else:
                    filename = col
                path_mod = pathlib.Path(path, subject_id, col, f"{filename}.nii.gz").as_posix()
                print(path_mod)
                #All modalities except RTSTRUCT should be of type torchIO.ScalarImage 
                if os.path.exists(path_mod):
                    if col.split("_")[0]!="RTSTRUCT":
                        temp[f"mod_{col}"] = tio.ScalarImage(path_mod)
                    else:
                        path_mods = [pathlib.Path(path, subject_id, col, f"{filename}.nii.gz").as_posix() for filename in filenames]
                        temp[f"mod_{col}"] = tio.LabelMap(path_mods)
                else:
                    temp[f"mod_{col}"] = None
                #For including metadata
                if metadata_name in imp_metadata:
                    #convert string to proper datatype
                    meta = df_metadata.loc[subject_id,metadata_name]
                    if pd.notna(meta):
                        temp[metadata_name] = eval(meta)[0]
                    else:
                        #torch dataloader doesnt accept None type
                        temp[metadata_name] = {}
            subjects.append(tio.Subject(temp))
        return cls(subjects, path)

    @classmethod
    def load_directly(
            cls,
            path:str,
            modalities: str,
            n_jobs: int = -1,
            spacing: Tuple = (1., 1., 0.),
            ignore_multi: bool = True,
            ) -> List[tio.Subject]:
        """
        Based on the given path, imgtools crawls through the directory, forms datagraph and picks the user defined modalities. These paths are processed into sitk.Image.
        This image and the metadata associated with it, creates a list of Subject instances
        Parameters
            path: Path to the directory of the dataset
        """
        input = ImageAutoInput(path, modalities, n_jobs)
        df_metadata = input.df_combined
        output_streams = input.output_streams
        #Ignores multiple connection to single modality
        if ignore_multi:
            output_streams = [items for items in output_streams if items.split("_")[-1].isnumeric()==False]
        #Basic operations
        subject_id_list = list(df_metadata.index)
        # basic image processing ops
        resample = Resample(spacing=spacing)
        make_binary_mask = StructureSetToSegmentation(roi_names=[], continuous=False)
        subjects =  Parallel(n_jobs=n_jobs)(delayed(cls.process_one_subject)(input,subject_id,output_streams,resample,make_binary_mask) for subject_id in tqdm(subject_id_list))
        return cls(subjects,path)

    @staticmethod
    def process_one_subject(
            input: Pipeline,
            subject_id: str,
            output_streams: List[str],
            resample: BaseOp,
            make_binary_mask: BaseOp,  
            ) -> tio.Subject:
        """
        Process all modalities for one subject
        Parameters:
            input: ImageAutoInput class which helps in loading the respective DICOMs
            subject_id: subject id of the data
            output_streams: the modalities that are being considered, Note that there can be multiple items of same modality based on their relations with different modalities
            resample: transformation which resamples sitk.Image
            make_binary_mask: transformation useful in making binary mask for rtstructs
        Returns tio.Subject instance for a particular subject id
        """
        temp = {}
        read_results = input(subject_id)
        for i,colname in enumerate(output_streams):
            modality = colname.split("_")[0]
            output_stream = ("_").join([item for item in colname.split("_") if item != "1"])

            if read_results[i] is None:
                temp[f"mod_{colname}"] = None
            elif modality == "CT":
                image = read_results[i]
                if len(image.GetSize()) == 4:
                    assert image.GetSize()[-1] == 1, f"There is more than one volume in this CT file for {subject_id}."
                    extractor = sitk.ExtractImageFilter()
                    extractor.SetSize([*image.GetSize()[:3], 0])
                    extractor.SetIndex([0, 0, 0, 0])    
                    image = extractor.Execute(image)
                image = resample(image)
                temp[f"mod_{colname}"] = tio.ScalarImage.from_sitk(image)
            elif modality == "RTDOSE":
                try: #For cases with no image present
                    doses = read_results[i].resample_dose(image)
                except:
                    Warning("No CT image present. Returning dose image without resampling")
                    doses = read_results[i]
                temp[f"mod_{colname}"] = tio.ScalarImage.from_sitk(doses)
                temp[f"metadata_{colname}"] = read_results[i].get_metadata()
            elif modality == "RTSTRUCT":
                #For RTSTRUCT, you need image or PT
                structure_set = read_results[i]
                conn_to = output_stream.split("_")[-1]
                # make_binary_mask relative to ct/pet
                if conn_to == "CT":
                    mask = make_binary_mask(structure_set, image)
                elif conn_to == "PT":
                    mask = make_binary_mask(structure_set, pet)
                else:
                    raise ValueError("You need to pass a reference CT or PT/PET image to map contours to.")
                temp[f"mod_{colname}"] = tio.LabelMap.from_sitk(mask)
                temp[f"metadata_{colname}"] = structure_set.roi_names
            elif modality == "PT":
                try:
                    #For cases with no image present
                    pet = read_results[i].resample_pet(image)
                except:
                    Warning("No CT image present. Returning PT/PET image without resampling.")
                    pet = read_results[i]
                temp[f"mod_{colname}"] = tio.ScalarImage.from_sitk(pet)
                temp[f"metadata_{colname}"] = read_results[i].get_metadata()
        return tio.Subject(temp)
