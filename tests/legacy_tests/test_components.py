import ast
import os
import pathlib

import pandas as pd
import pytest
import SimpleITK as sitk

from imgtools._deprecated.autopipeline import AutoPipeline
from imgtools.logging import logger


# @pytest.mark.parametrize("modalities",["PT", "CT,RTSTRUCT", "CT,RTDOSE", "CT,PT,RTDOSE", "CT,RTSTRUCT,RTDOSE", "CT,RTSTRUCT,RTDOSE,PT"])
@pytest.mark.parametrize(
    "modalities", ["CT", "CT,RTSTRUCT", "CT,RTSTRUCT,RTDOSE"]
)  # , "CT,RTDOSE,PT"])
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
    def _get_path(
        self, legacy_test_data
    ) -> None:  # dataset_path is a fixture defined in conftest.py
        self.input_path, self.output_path, self.crawl_path, self.edge_path = (
            legacy_test_data
        )
        logger.info(legacy_test_data)

    def test_pipeline(self, modalities) -> None:
        """
        Testing the Autopipeline for processing the DICOMS and saving it as nrrds
        """
        n_jobs = 1
        output_path_mod = pathlib.Path(
            self.output_path, str("temp_folder_" + ("_").join(modalities.split(",")))
        ).as_posix()
        # Initialize pipeline for the current setting
        pipeline = AutoPipeline(
            self.input_path,
            output_path_mod,
            modalities,
            n_jobs=n_jobs,
            spacing=(5, 5, 5),
            overwrite=True,
            update=True,
        )
        # Run for different modalities
        comp_path = pathlib.Path(output_path_mod, "dataset.csv").as_posix()
        pipeline.run()

        # Check if the crawl and edges exist
        assert os.path.exists(self.crawl_path) & os.path.exists(self.edge_path), (
            "There was no crawler output"
        )

        # for the test example, there are 6 files and 4 connections
        crawl_data = pd.read_csv(self.crawl_path, index_col=0)
        edge_data = pd.read_csv(self.edge_path)
        # this assert will fail....
        assert (len(crawl_data) == 12) & (len(edge_data) == 10), (
            "There was an error in crawling or while making the edge table"
        )

        # Check if the dataset.csv is having the correct number of components and has all the fields
        comp_table = pd.read_csv(comp_path, index_col=0)
        assert len(comp_table) == 2, (
            "There was some error in making components, check datagraph.parser"
        )

        # Check the nrrd files
        subject_id_list = list(comp_table.index)
        output_streams = [
            ("_").join(cols.split("_")[2:])
            for cols in comp_table.columns
            if cols.split("_")[0] == "output"
        ]
        for subject_id in subject_id_list:
            shapes = []
            for col in output_streams:
                if "RTSTRUCT" in col:
                    filename = ast.literal_eval(
                        comp_table.loc[subject_id]["metadata_RTSTRUCT_CT"]
                    )[0][0]
                else:
                    filename = col

                path_mod = pathlib.Path(
                    output_path_mod, subject_id, col, f"{filename}.nii.gz"
                ).as_posix()
                # All modalities except RTSTRUCT should be of type torchIO.ScalarImage
                temp_dicom = sitk.GetArrayFromImage(sitk.ReadImage(path_mod))
                shapes.append(temp_dicom.shape)
            A = [item == shapes[0] for item in shapes]
            assert all(A)
