import numpy as np
import pytest 
import SimpleITK as sitk
from pathlib import Path
from imgtools.modules import Segmentation, StructureSet
from imgtools.io import read_dicom_rtstruct, read_dicom_series
from imgtools.ops import StructureSetToSegmentation


@pytest.fixture
def HNPCT_data(data_paths) -> dict[str, Path | str]:
    dataset_key = 'Head-Neck-PET-CT'
    parent_dir_path = data_paths[dataset_key]
    image_path = parent_dir_path / "HN-CHUS-052/08-27-1885-CA ORL FDG TEP POS TX-94629/3.000000-Merged-06362/"
    mask_path = parent_dir_path / "HN-CHUS-052/08-27-1885-OrophCB.0OrophCBTRTID derived StudyInstanceUID.-94629/Pinnacle POI-41418/1-1.dcm"
    return {"image": image_path, "mask": mask_path, "roi_name": "GTV1"}

@pytest.fixture
def image_CT(HNPCT_data) -> sitk.Image:
    image = read_dicom_series(HNPCT_data["image"].resolve())
    return image

@pytest.fixture
def mask_RT(HNPCT_data, image_CT) -> sitk.Image:
    image_data = HNPCT_data
    reference_image = image_CT

    # Load just the GTV ROI into a StructureSet object
    rt_structure_set = StructureSet.from_dicom_rtstruct(image_data['mask'], roi_name_pattern=image_data['roi_name'])

    # Initialize a mask with the same size as the reference image
    size = reference_image.GetSize()[::-1] + (1,)
    mask = np.zeros(size, dtype=np.uint8)

    # Convert StructureSet points to a binary mask
    rt_structure_set.get_mask(reference_image = reference_image, 
                              mask = mask, 
                              label = 1, 
                              idx = 1, 
                              continuous = False)

    # Convert the mask from an nd.array to a SimpleITK Image
    mask = sitk.GetImageFromArray(mask)
    # Copy metadata from the reference image to the mask
    mask.CopyInformation(reference_image)

    return mask



def test_base_segmentation_construction(mask_RT):
    "Test default Segmentation construction"
    segmentation = Segmentation(mask_RT)

    assert segmentation.raw_roi_names == {}
    assert segmentation.metadata == {}
    assert segmentation.num_labels == 1
    assert segmentation.frame_groups is None

    assert len(segmentation.roi_indices) == 1
    assert 'label_1' in segmentation.roi_indices
    assert segmentation.roi_indices['label_1'] == 1


# def test_segmentation_construction_with_roi_indices():
#     "Test Segmentation construction with roi_indices"
#     mask = example_data()['mask']
#     segmentation = Segmentation(mask, roi_indices={'star': 1})

#     assert segmentation.raw_roi_names == {}
#     assert segmentation.metadata == {}
#     assert segmentation.num_labels == 1

#     assert len(segmentation.roi_indices) == 1
#     assert 'star' in segmentation.roi_indices
#     assert segmentation.roi_indices['star'] == 1


# def test_segmentation_construction_with_existing_roi_indices():
#     "Test Segmentation construction with roi_indices"
#     mask = example_data()['mask']
#     segmentation = Segmentation(mask, roi_indices={'star': 1}, existing_roi_indices={'background': 0})

#     assert segmentation.raw_roi_names == {}
#     assert segmentation.metadata == {}
#     assert segmentation.num_labels == 1

#     assert len(segmentation.roi_indices) == 1
#     assert 'star' in segmentation.roi_indices
#     assert segmentation.roi_indices['star'] == 1

#     assert len(segmentation.roi_indices) == 1
#     assert 'background' in segmentation.roi_indices
#     assert segmentation.roi_indices['background'] == 0


# @pytest.fixture
# def segmentation():
#     # Segmentation object
#     mask = example_data()['mask']
#     return Segmentation.from_dicom(mask, roi_indices={'star': 1}, existing_roi_indices={'background': 0})

# def star_mask(segmentation):
#     # SimpleITK Image of the star mask
#     return segmentation[0]


# def test_get_label_from_name(segmentation, name = 'star'):
#     actual_label = segmentation.get_label_from_name(name = name)
#     assert actual_label == 1

# @pytest.mark.parameterize(
#     "label, name",
#     [
#         1, None,
#         None, "star"
#     ]
# )
# def test_get_label(segmentation, label, name):
#     actual_image = segmentation.get_label(label = label, name = name)

#     pass



