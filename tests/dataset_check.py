"""
This file does not get tested because it doesnt start with test_ and so, is not a part of the test suite.

Leaving here for future reference.
"""

import os
import pathlib
import re
from typing import List
from urllib import request
from zipfile import ZipFile

import pandas as pd
import pytest
import torch
import torchio as tio

from imgtools.io import Dataset


@pytest.fixture(scope='session')
def dataset_path():
    curr_path = pathlib.Path(__file__).parent.parent.resolve()
    quebec_path = pathlib.Path(pathlib.Path(curr_path, 'data', 'Head-Neck-PET-CT').as_posix())

    if not os.path.exists(quebec_path):
        pathlib.Path(quebec_path).mkdir(parents=True, exist_ok=True)
        # Download QC dataset
        quebec_data_url = (
            'https://github.com/bhklab/tcia_samples/blob/main/Head-Neck-PET-CT.zip?raw=true'
        )
        quebec_zip_path = pathlib.Path(quebec_path, 'Head-Neck-PET-CT.zip').as_posix()
        request.urlretrieve(quebec_data_url, quebec_zip_path)
        with ZipFile(quebec_zip_path, 'r') as zipfile:
            zipfile.extractall(quebec_path)
        os.remove(quebec_zip_path)
    else:
        pass
    output_path = pathlib.Path(curr_path, 'tests', 'temp').as_posix()
    quebec_path = quebec_path.as_posix()

    # Dataset name
    dataset_name = os.path.basename(quebec_path)
    imgtools_path = pathlib.Path(os.path.dirname(quebec_path), '.imgtools')

    # Defining paths for autopipeline and dataset component
    crawl_path = pathlib.Path(imgtools_path, f'imgtools_{dataset_name}.csv').as_posix()
    json_path = pathlib.Path(imgtools_path, f'imgtools_{dataset_name}.json').as_posix()  # noqa: F841
    edge_path = pathlib.Path(imgtools_path, f'imgtools_{dataset_name}_edges.csv').as_posix()
    assert (
        os.path.exists(crawl_path) & os.path.exists(edge_path) & os.path.exists(json_path)
    ), 'There was no crawler output'

    yield quebec_path, output_path, crawl_path, edge_path


class select_roi_names(tio.LabelTransform):
    """
    Based on the given roi names, selects from the given set
    """

    def __init__(self, roi_names: List[str] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.kwargs = kwargs
        self.roi_names = roi_names

    def apply_transform(self, subject):
        # list of roi_names
        for image in self.get_images(subject):
            # For only applying to labelmaps
            metadata = subject['metadata_RTSTRUCT_CT']
            patterns = self.roi_names
            mask = torch.empty_like(image.data)[: len(patterns)]
            for j, pat in enumerate(patterns):
                k = []
                for i, col in enumerate(metadata):
                    if re.match(pat, col, flags=re.IGNORECASE):
                        k.append(i)
                if len(k) == 0:
                    mask[j] = mask[j] * 0
                else:
                    mask[j] = (image.data[k].sum(axis=0) > 0) * 1
            image.set_data(mask)
        return subject

    def is_invertible(self) -> bool:
        return False


# Defining for test_dataset method in Test_components class
def collate_fn(data):
    """
    data: is a tio.subject with multiple columns
          Need to return required data
    """
    mod_names = [items for items in data[0] if items.split('_')[0] == 'mod']
    temp_stack = {}
    for names in mod_names:
        temp_stack[names] = torch.stack(tuple(items[names].data for items in data))
    return temp_stack


@pytest.mark.parametrize('modalities', ['CT', 'CT,RTSTRUCT', 'CT,RTSTRUCT,RTDOSE'])
class TestDataset:
    """
    For testing the dataset components of the med-imagetools package
    test_dataset:
        1) Checks if the length of the dataset matches
        2) Checks if the items in the subject object is correct and present
        3) Checks if you are able to load it via load_nrrd and load_directly, and checks if the subjects generated matches
        4) Checks if torch data loader can load the formed dataset and get atleast 1 iteration
        5) Checks if the transforms are happening by checking the size
    """

    @pytest.fixture(autouse=True)
    def _get_path(self, dataset_path) -> None:
        self.input_path, self.output_path, self.crawl_path, self.edge_path = dataset_path

    def test_dataset(self, modalities) -> None:
        """
        Testing the Dataset class
        """
        output_path_mod = pathlib.Path(
            self.output_path, str('temp_folder_' + ('_').join(modalities.split(',')))
        ).as_posix()
        comp_path = pathlib.Path(output_path_mod).resolve().joinpath('dataset.csv').as_posix()
        pd.read_csv(comp_path, index_col=0)

        # Loading from nrrd files
        subjects_nrrd = Dataset.load_image(output_path_mod, ignore_multi=True)
        # Loading files directly
        # subjects_direct = Dataset.load_directly(self.input_path,modalities=modalities,ignore_multi=True)

        # The number of subjects is equal to the number of components which is 2 for this dataset
        # assert len(subjects_nrrd) == len(subjects_direct) == 2, "There was some error in generation of subject object"
        # assert subjects_nrrd[0].keys() == subjects_direct[0].keys()

        # del subjects_direct
        # To check if all metadata items present in the keys
        # temp_nrrd = subjects_nrrd[0]
        # columns_shdbe_present = set([col if col.split("_")[0]=="metadata" else "mod_"+("_").join(col.split("_")[1:]) for col in list(comp_table.columns) if col.split("_")[0] in ["folder","metadata"]])
        # print(columns_shdbe_present)
        # assert set(temp_nrrd.keys()).issubset(columns_shdbe_present), "Not all items present in dictionary, some fault in going through the different columns in a single component"

        transforms = tio.Compose(
            [
                tio.Resample(4),
                tio.CropOrPad((96, 96, 40)),
                select_roi_names(['larynx']),
                tio.OneHot(),
            ]
        )

        # Forming dataset and dataloader
        test_set = tio.SubjectsDataset(subjects_nrrd, transform=transforms)
        test_loader = torch.utils.data.DataLoader(
            test_set, batch_size=2, shuffle=True, collate_fn=collate_fn
        )

        # Check test_set is correct
        assert len(test_set) == 2

        # Get items from test loader
        # If this function fails , there is some error in formation of test
        data = next(iter(test_loader))
        A = [
            item[1].shape == (2, 1, 96, 96, 40)
            if 'RTSTRUCT' not in item[0]
            else item[1].shape == (2, 2, 96, 96, 40)
            for item in data.items()
        ]
        assert all(A), 'There is some problem in the transformation/the formation of subject object'
