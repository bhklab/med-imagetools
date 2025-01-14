import os
import pathlib
from urllib import request
from zipfile import ZipFile

import pytest

from imgtools.logging import logger


@pytest.fixture(scope='session')
def curr_path():
    return pathlib.Path(__file__).parent.parent.resolve().as_posix()


@pytest.fixture(scope='session')
def dataset_path(curr_path):
    quebec_path = pathlib.Path(curr_path, 'data', 'Head-Neck-PET-CT')

    if not (quebec_path.exists() and len(list(quebec_path.glob('*'))) == 2):
        quebec_path.mkdir(parents=True, exist_ok=True)

        # Download QC dataset
        logger.info('Downloading the test dataset...')
        quebec_data_url = (
            'https://github.com/bhklab/tcia_samples/blob/main/Head-Neck-PET-CT.zip?raw=true'
        )
        quebec_zip_path = pathlib.Path(quebec_path, 'Head-Neck-PET-CT.zip').as_posix()
        request.urlretrieve(quebec_data_url, quebec_zip_path)
        with ZipFile(quebec_zip_path, 'r') as zipfile:
            zipfile.extractall(quebec_path)
        os.remove(quebec_zip_path)
    else:
        logger.info('Data already downloaded...')

    output_path = pathlib.Path(curr_path, 'tests', 'temp').as_posix()
    quebec_path = quebec_path.as_posix()

    # Dataset name
    dataset_name = os.path.basename(quebec_path)
    imgtools_path = pathlib.Path(os.path.dirname(quebec_path), '.imgtools')

    # Defining paths for autopipeline and dataset component
    crawl_path = pathlib.Path(imgtools_path, f'imgtools_{dataset_name}.csv').as_posix()
    edge_path = pathlib.Path(imgtools_path, f'imgtools_{dataset_name}_edges.csv').as_posix()
    # json_path =  pathlib.Path(imgtools_path, f"imgtools_{dataset_name}.json").as_posix()  # noqa: F841

    yield quebec_path, output_path, crawl_path, edge_path


@pytest.fixture(scope='session')
def modalities_path(curr_path):
    qc_path = pathlib.Path(curr_path, 'data', 'Head-Neck-PET-CT', 'HN-CHUS-052')
    assert qc_path.exists(), 'Dataset not found'

    path = {}
    path['CT'] = pathlib.Path(
        qc_path, '08-27-1885-CA ORL FDG TEP POS TX-94629/3.000000-Merged-06362'
    ).as_posix()
    path['RTSTRUCT'] = pathlib.Path(
        qc_path,
        '08-27-1885-OrophCB.0OrophCBTRTID derived StudyInstanceUID.-94629/Pinnacle POI-41418',
    ).as_posix()
    path['RTDOSE'] = pathlib.Path(
        qc_path,
        '08-27-1885-OrophCB.0OrophCBTRTID derived StudyInstanceUID.-94629/11376',
    ).as_posix()
    path['PT'] = pathlib.Path(
        qc_path, '08-27-1885-CA ORL FDG TEP POS TX-94629/532790.000000-LOR-RAMLA-44600'
    ).as_posix()
    return path
