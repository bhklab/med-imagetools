import numpy as np
import pytest 
import SimpleITK as sitk
from pathlib import Path
from imgtools.modules import Segmentation, StructureSet
from imgtools.io import read_dicom_series
from imgtools.coretypes import RegionBox, Coordinate3D, Size3D

@pytest.fixture
def HNPCT_paths():
    return {
        "base_image_path": Path("Head-Neck-PET-CT/HN-CHUS-052/08-27-1885-CA ORL FDG TEP POS TX-94629/3.000000-Merged-06362"),
        "mask_path": Path("Head-Neck-PET-CT/HN-CHUS-052/08-27-1885-OrophCB.0OrophCBTRTID derived StudyInstanceUID.-94629/Pinnacle POI-41418/1-1.dcm")
    }

@pytest.fixture
def HNPCT_roi_name():
    return "GTV1"

@pytest.fixture
def NSCLC_Radiomics():
    return {
        "dataset_name": "NSCLC-Radiomics",
        "base_image_path": Path("NSCLC-Radiomics/LUNG1-001/1.3.6.1.4.1.32722.99.99.298991776521342375010861296712563382046"),
        "mask_path": Path("NSCLC-Radiomics/LUNG1-001/1.3.6.1.4.1.32722.99.99.227938121586608072508444156170535578236/00000001.dcm")
    }

@pytest.fixture
def NSCLC_Radiomics_roi_name():
    return "GTV-1"

@pytest.fixture
def image_data_paths(data_paths, NSCLC_Radiomics) -> dict[str, Path]:
    parent_dir_path = data_paths[NSCLC_Radiomics["dataset_name"]].parent
    image_path = parent_dir_path / NSCLC_Radiomics['base_image_path']
    mask_path = parent_dir_path / NSCLC_Radiomics['mask_path']
    return {"image_path": image_path, "mask_path": mask_path}
    

@pytest.fixture
def image_CT(image_data_paths) -> sitk.Image:
    return read_dicom_series(image_data_paths["image_path"].resolve())

@pytest.fixture
def structure_set_RT(image_data_paths) -> StructureSet:
    # Load just the GTV ROI into a StructureSet object
    return StructureSet.from_dicom_rtstruct(image_data_paths['mask_path'])

@pytest.fixture
def segmentation_RT(structure_set_RT, image_CT) -> Segmentation:
    # Convert the StructureSet object to a Segmentation object
    return structure_set_RT.to_segmentation(reference_image=image_CT, 
                                            roi_names = structure_set_RT.roi_names, 
                                            continuous = False)
    


def test_get_label_from_name(segmentation_RT, NSCLC_Radiomics_roi_name):
    actual_label = segmentation_RT.get_label_from_name(name = NSCLC_Radiomics_roi_name)
    assert actual_label == 1


@pytest.mark.parametrize(
    "label, name",
    [
       (1, None),
       (None, "GTV-1")
    ]
)
def test_get_label(segmentation_RT, label, name, image_CT):
    actual_image = segmentation_RT.get_label(label, name)

    assert actual_image.GetSize() == image_CT.GetSize()
    assert isinstance(actual_image, sitk.Image)
    assert actual_image.GetSpacing() == image_CT.GetSpacing()
    assert actual_image.GetOrigin() == image_CT.GetOrigin()



def test_compute_statistics(segmentation_RT):
    label_image = segmentation_RT.get_label(name = "GTV-1")
    stats = segmentation_RT.compute_statistics(label_image)
    assert isinstance(stats, sitk.LabelShapeStatisticsImageFilter)
    print(stats.GetNumberOfLabels())
    assert stats.GetNumberOfLabels() == 1
    assert stats.GetNumberOfPixels(label=1) == 56271


def test_get_label_bounding_box(segmentation_RT):
    reg_box = segmentation_RT.get_label_bounding_box(name = "GTV-1")

    assert isinstance(reg_box, RegionBox)
    assert reg_box.min == Coordinate3D(290, 226, 65)
    assert reg_box.max == Coordinate3D(388, 317, 86)
    assert reg_box.size == Size3D(98, 91, 21)


def test_get_label_dimensions(segmentation_RT):
    dims = segmentation_RT.get_label_dimensions(name = "GTV-1")
    assert dims == Size3D(98, 91, 21)


def test_get_label_number_of_pixels(segmentation_RT):
    num_pixels = segmentation_RT.get_label_number_of_pixels(name = "GTV-1")
    assert num_pixels == 56271

