import os
import shutil
import pathlib
import urllib.request as request
from zipfile import ZipFile

import pytest
import pandas as pd
import nrrd

from imgtools.autopipeline import AutoPipeline

@pytest.fixture
def dataset_path():
    curr_path = pathlib.Path(__file__).parent.parent.resolve()
    quebec_path = pathlib.Path(os.path.join(curr_path, "data", "Head-Neck-PET-CT"))
    pathlib.Path(quebec_path).mkdir(parents=True, exist_ok=True)
    
    # Download QC dataset
    quebec_data_url = "https://github.com/bhklab/tcia_samples/blob/main/Head-Neck-PET-CT.zip?raw=true"
    quebec_zip_path = os.path.join(quebec_path, "Head-Neck-PET-CT.zip")
    request.urlretrieve(quebec_data_url, quebec_zip_path) 
    with ZipFile(quebec_zip_path, 'r') as zipfile:
        zipfile.extractall(quebec_path)
    os.remove(quebec_zip_path)

    output_path = pathlib.Path(os.path.join(curr_path, 'tests'))
    return quebec_path.as_posix(), output_path.as_posix()

# @pytest.mark.parametrize("modalities",["PT","CT,RTDOSE","CT,RTSTRUCT,RTDOSE","CT,RTSTRUCT,RTDOSE,PT"])
@pytest.mark.parametrize("modalities", ["CT,PT,RTDOSE"])
def test_pipeline(dataset_path, modalities):
    input_path, output_path = dataset_path
    dataset_name = os.path.basename(input_path)
    n_jobs = 2
    output_path_mod = os.path.join(output_path, str("temp_folder_" + ("_").join(modalities.split(","))))
    #Initialize pipeline for the current setting
    pipeline = AutoPipeline(input_path, output_path_mod, modalities, n_jobs=n_jobs)
    #Run for different modalities
    comp_path = os.path.join(output_path_mod, "dataset.csv")
    pipeline.run()

    #Check if the crawl and edges exist
    crawl_path = os.path.join(os.path.dirname(input_path), f"imgtools_{dataset_name}.csv")
    json_path =  os.path.join(os.path.dirname(input_path), f"imgtools_{dataset_name}.json")
    edge_path = os.path.join(os.path.dirname(input_path), f"imgtools_{dataset_name}_edges.csv")
    assert os.path.exists(crawl_path) & os.path.exists(edge_path), "There was no crawler output"

    #for the test example, there are 6 files and 4 connections
    crawl_data = pd.read_csv(crawl_path, index_col = 0)
    edge_data = pd.read_csv(edge_path)
    assert (len(crawl_data) == 12) & (len(edge_data) == 8), "There was an error in crawling or while making the edge table"

    #Check if the dataset.csv is having the correct number of components and has all the fields
    comp_table = pd.read_csv(comp_path)
    assert len(comp_table) == 2, "There was some error in making components, check datagraph.parser"

    #Check the nrrd files
    if modalities   == "PT":
        path_pet    = os.path.join(output_path_mod, "pet", os.listdir(os.path.join(output_path_mod,"pet"))[0])
        dicom, _    = nrrd.read(path_pet)
        assert dicom.shape[-1] == int(crawl_data.loc[crawl_data["modality"]=="PT","instances"].values[0])
    elif modalities == "CT,RTDOSE":
        path_ct     = os.path.join(output_path_mod, "image", os.listdir(os.path.join(output_path_mod,"image"))[0])
        path_dose   = os.path.join(output_path_mod, "dose", os.listdir(os.path.join(output_path_mod,"dose"))[0])
        dicom_ct, _ = nrrd.read(path_ct)
        dicom_dose, _ = nrrd.read(path_dose)
        assert dicom_ct.shape == dicom_dose.shape
    elif modalities == "CT,PT,RTDOSE":
        path_ct         = os.path.join(output_path_mod, "image", os.listdir(os.path.join(output_path_mod,"image"))[0])
        path_dose       = os.path.join(output_path_mod, "dose", os.listdir(os.path.join(output_path_mod,"dose"))[0])
        path_pet        = os.path.join(output_path_mod, "pet", os.listdir(os.path.join(output_path_mod,"pet"))[0])
        dicom_ct, _     = nrrd.read(path_ct)
        dicom_dose, _   = nrrd.read(path_dose)
        dicom_pet, _    = nrrd.read(path_pet)
        print(dicom_ct.shape, dicom_dose.shape, dicom_pet.shape)
        assert dicom_ct.shape == dicom_dose.shape == dicom_pet.shape
    elif modalities == "CT,RTSTRUCT,RTDOSE":
        path_ct         = os.path.join(output_path_mod, "image", os.listdir(os.path.join(output_path_mod,"image"))[0])
        path_dose       = os.path.join(output_path_mod, "dose", os.listdir(os.path.join(output_path_mod,"dose"))[0])
        path_str        = os.path.join(output_path_mod, "mask_ct", os.listdir(os.path.join(output_path_mod,"mask_ct"))[0])
        dicom_ct, _     = nrrd.read(path_ct)
        dicom_dose, _   = nrrd.read(path_dose)
        dicom_str, _    = nrrd.read(path_str)
        #ensure they are in same physical space
        assert dicom_ct.shape == dicom_dose.shape == dicom_str.shape[1:]
    else:
        path_ct         = os.path.join(output_path_mod, "image", os.listdir(os.path.join(output_path_mod,"image"))[0])
        path_dose       = os.path.join(output_path_mod, "dose", os.listdir(os.path.join(output_path_mod,"dose"))[0])
        path_ctstr      = os.path.join(output_path_mod, "mask_ct", os.listdir(os.path.join(output_path_mod,"mask_ct"))[0])
        path_ptstr      = os.path.join(output_path_mod, "mask_pt", os.listdir(os.path.join(output_path_mod,"mask_pt"))[0])
        path_pet        = os.path.join(output_path_mod, "pet", os.listdir(os.path.join(output_path_mod,"pet"))[0])
        dicom_ct, _     = nrrd.read(path_ct)
        dicom_dose, _   = nrrd.read(path_dose)
        dicom_ctstr, _  = nrrd.read(path_ctstr)
        dicom_ptstr, _  = nrrd.read(path_ptstr)
        dicom_pet, _    = nrrd.read(path_pet)

        #ensure they are in same physical space
        assert dicom_ct.shape == dicom_dose.shape == dicom_ctstr.shape[1:] == dicom_ptstr.shape[1:] == dicom_pet.shape
    
    os.remove(crawl_path)
    os.remove(json_path)
    os.remove(edge_path)
    shutil.rmtree(output_path_mod)


