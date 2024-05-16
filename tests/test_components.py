import os
import pathlib
import urllib.request as request
from zipfile import ZipFile

import pytest
import SimpleITK as sitk
import pandas as pd
from imgtools.autopipeline import AutoPipeline
import ast

@pytest.fixture(scope="session")
def dataset_path():
    curr_path = pathlib.Path(__file__).parent.parent.resolve()
    quebec_path = pathlib.Path(pathlib.Path(curr_path, "data", "Head-Neck-PET-CT").as_posix())
    
    if not os.path.exists(quebec_path):
        pathlib.Path(quebec_path).mkdir(parents=True, exist_ok=True)
        # Download QC dataset
        print("Downloading the test dataset...")
        quebec_data_url = "https://github.com/bhklab/tcia_samples/blob/main/Head-Neck-PET-CT.zip?raw=true"
        quebec_zip_path = pathlib.Path(quebec_path, "Head-Neck-PET-CT.zip").as_posix()
        request.urlretrieve(quebec_data_url, quebec_zip_path)
        with ZipFile(quebec_zip_path, 'r') as zipfile:
            zipfile.extractall(quebec_path)
        os.remove(quebec_zip_path)
    else:
        print("Data already downloaded...")
    output_path = pathlib.Path(curr_path, 'tests','temp').as_posix()
    quebec_path = quebec_path.as_posix()
    
    #Dataset name
    dataset_name  = os.path.basename(quebec_path)
    imgtools_path = pathlib.Path(os.path.dirname(quebec_path), '.imgtools')

    #Defining paths for autopipeline and dataset component
    crawl_path = pathlib.Path(imgtools_path, f"imgtools_{dataset_name}.csv").as_posix()
    json_path =  pathlib.Path(imgtools_path, f"imgtools_{dataset_name}.json").as_posix()  # noqa: F841
    edge_path = pathlib.Path(imgtools_path, f"imgtools_{dataset_name}_edges.csv").as_posix()
    yield quebec_path, output_path, crawl_path, edge_path




# @pytest.mark.parametrize("modalities",["PT", "CT,RTSTRUCT", "CT,RTDOSE", "CT,PT,RTDOSE", "CT,RTSTRUCT,RTDOSE", "CT,RTSTRUCT,RTDOSE,PT"])
@pytest.mark.parametrize("modalities", ["CT", "CT,RTSTRUCT", "CT,RTSTRUCT,RTDOSE"])#, "CT,RTDOSE,PT"])
class TestComponents:
    """
    For testing the autopipeline components of the med-imagetools package
    It has two methods:
    test_pipeline:
        1) Checks if there is any crawler and edge table output generated by autopipeline
        2) Checks if for the test data, the lengths of the crawler and edge table matches the actual length of what should be ideally created
        3) Checks if the length of component table(dataset.csv) is correct or not
        4) Checks for every component, the shape of all different modalities matches or not

    """
    @pytest.fixture(autouse=True)
    def _get_path(self, dataset_path):
        self.input_path, self.output_path, self.crawl_path, self.edge_path = dataset_path
        print(dataset_path)
    
    def test_pipeline(self, modalities):
        """
        Testing the Autopipeline for processing the DICOMS and saving it as nrrds
        """
        n_jobs = 2
        output_path_mod = pathlib.Path(self.output_path, str("temp_folder_" + ("_").join(modalities.split(",")))).as_posix()
        #Initialize pipeline for the current setting
        pipeline = AutoPipeline(self.input_path, output_path_mod, modalities, n_jobs=n_jobs,spacing=(5,5,5), overwrite=True)
        #Run for different modalities
        comp_path = pathlib.Path(output_path_mod, "dataset.csv").as_posix()
        pipeline.run()

        #Check if the crawl and edges exist
        assert os.path.exists(self.crawl_path) & os.path.exists(self.edge_path), "There was no crawler output"

        #for the test example, there are 6 files and 4 connections
        crawl_data = pd.read_csv(self.crawl_path, index_col=0)
        edge_data = pd.read_csv(self.edge_path)
        # this assert will fail....
        assert (len(crawl_data) == 12) & (len(edge_data) == 10), "There was an error in crawling or while making the edge table"

        #Check if the dataset.csv is having the correct number of components and has all the fields
        comp_table = pd.read_csv(comp_path, index_col=0)
        assert len(comp_table) == 2, "There was some error in making components, check datagraph.parser"

        #Check the nrrd files
        subject_id_list = list(comp_table.index)
        output_streams = [("_").join(cols.split("_")[2:]) for cols in comp_table.columns if cols.split("_")[0] == "output"]
        for subject_id in subject_id_list:
            shapes = []
            for col in output_streams:
                if 'RTSTRUCT' in col:
                    filename = ast.literal_eval(comp_table.loc[subject_id]['metadata_RTSTRUCT_CT'])[0][0]
                else:
                    filename = col
                
                print(subject_id, col, filename)
                path_mod = pathlib.Path(output_path_mod, subject_id, col, f"{filename}.nii.gz").as_posix()
                # All modalities except RTSTRUCT should be of type torchIO.ScalarImage
                temp_dicom = sitk.GetArrayFromImage(sitk.ReadImage(path_mod))
                shapes.append(temp_dicom.shape)
            A = [item == shapes[0] for item in shapes]
            print(shapes)
            assert all(A)
    