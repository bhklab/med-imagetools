import os
from posixpath import dirname
import shutil
import warnings
from multiprocessing import cpu_count

import numpy as np
import SimpleITK as sitk
import pytest
import nrrd
import pandas as pd

from imgtools.autopipeline import AutoPipeline

@pytest.fixture
def dataset_path():
    curr_path=("/").join(os.getcwd().split("/")[:-1])
    input_path = curr_path+ "/examples/data_test"
    output_path = curr_path+ "/tests/"
    return input_path,output_path

@pytest.mark.parametrize("modalities",["PT","CT,RTDOSE","CT,RTSTRUCT,RTDOSE","CT,RTSTRUCT,RTDOSE,PT"])
def test_pipeline(dataset_path,modalities):
    input_path,output_path = dataset_path
    n_jobs = 2
    output_path_mod = output_path + "temp_folder_" + ("_").join(modalities.split(","))
    #Initialize pipeline for the current setting
    pipeline = AutoPipeline(input_path,output_path_mod,modalities,n_jobs=n_jobs)
    #Run for different modalities
    comp_path = os.path.join(output_path_mod, "dataset.csv")
    pipeline.run()

    #Check if the crawl and edges exist
    crawl_path = ("/").join(input_path.split("/")[:-1]) + "/imgtools_" + input_path.split("/")[-1] + ".csv"
    json_path =  ("/").join(input_path.split("/")[:-1]) + "/imgtools_" + input_path.split("/")[-1] + ".json"
    edge_path = ("/").join(input_path.split("/")[:-1]) + "/imgtools_" + input_path.split("/")[-1] + "_edges.csv"
    assert os.path.exists(crawl_path) & os.path.exists(edge_path), "this breaks because there was no crawler output"

    #for the test example, there are 6 files and 4 connections
    crawl_data = pd.read_csv(crawl_path,index_col = 0)
    edge_data = pd.read_csv(edge_path)
    assert (len(crawl_data)==7) & (len(edge_data)==4), "this breaks because there was some error in crawling or while making the edge table"

    #Check if the dataset.csv is having the correct number of components and has all the fields
    comp_table = pd.read_csv(comp_path)
    assert len(comp_table)==1, "this breaks because there is some error in making components, check datagraph.parser"

    #Check the nrrd files
    if modalities=="PT":
        path_pet = output_path_mod + "/pet/" + os.listdir(output_path_mod+"/pet")[0]
        dicom,_ = nrrd.read(path_pet)
        assert dicom.shape[-1] == int(crawl_data.loc[crawl_data["modality"]=="PT","instances"].values[0])
    elif modalities=="CT,RTDOSE":
        path_ct = output_path_mod + "/image/" + os.listdir(output_path_mod+"/image")[0]
        path_dose = output_path_mod + "/dose/" + os.listdir(output_path_mod+"/dose")[0]
        dicom_ct,_ = nrrd.read(path_ct)
        dicom_dose,_ = nrrd.read(path_dose)
        assert dicom_ct.shape == dicom_dose.shape
    elif modalities=="CT,RTSTRUCT,RTDOSE":
        path_ct = output_path_mod + "/image/" + os.listdir(output_path_mod+"/image")[0]
        path_dose = output_path_mod + "/dose/" + os.listdir(output_path_mod+"/dose")[0]
        path_str = output_path_mod + "/mask_ct/" + os.listdir(output_path_mod+"/mask_ct")[0]
        dicom_ct,_ = nrrd.read(path_ct)
        dicom_dose,_ = nrrd.read(path_dose)
        dicom_str,_ = nrrd.read(path_str)
        #ensure they are in same physical space
        assert dicom_ct.shape == dicom_dose.shape == dicom_str.shape[1:]
    else:
        path_ct = output_path_mod + "/image/" + os.listdir(output_path_mod+"/image")[0]
        path_dose = output_path_mod + "/dose/" + os.listdir(output_path_mod+"/dose")[0]
        path_ctstr = output_path_mod + "/mask_ct/" + os.listdir(output_path_mod+"/mask_ct")[0]
        path_ptstr = output_path_mod + "/mask_pt/" + os.listdir(output_path_mod+"/mask_pt")[0]
        path_pet = output_path_mod + "/pet/" + os.listdir(output_path_mod+"/pet")[0]
        dicom_ct,_ = nrrd.read(path_ct)
        dicom_dose,_ = nrrd.read(path_dose)
        dicom_ctstr,_ = nrrd.read(path_ctstr)
        dicom_ptstr,_ = nrrd.read(path_ptstr)
        dicom_pet,_ = nrrd.read(path_pet)
        #ensure they are in same physical space
        assert dicom_ct.shape == dicom_dose.shape == dicom_ctstr.shape[1:] == dicom_ptstr.shape[1:] == dicom_pet.shape
        os.remove(crawl_path)
        os.remove(json_path)
        os.remove(edge_path)
    shutil.rmtree(output_path_mod)


