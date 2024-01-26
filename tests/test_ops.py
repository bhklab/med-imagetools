import pytest
import SimpleITK as sitk
from imgtools.ops import FilterSegmentation

@pytest.fixture
def reference_image():
    # Create a reference image for testing
    size = (100, 100, 100)
    spacing = (1.0, 1.0, 1.0)
    origin = (0.0, 0.0, 0.0)
    direction = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
    return sitk.Image(size, sitk.sitkFloat32), spacing, origin, direction

def test_filter_segmentation(reference_image):
    # Create a test segmentation
    seg = sitk.Image(reference_image[0].GetSize(), sitk.sitkUInt8)
    seg.SetSpacing(reference_image[1])
    seg.SetOrigin(reference_image[2])
    seg.SetDirection(reference_image[3])
    seg_arr = sitk.GetArrayFromImage(seg)
    seg_arr[50:70, 50:70, 50:70] = 1
    seg = sitk.GetImageFromArray(seg_arr)

    # Create a test instance of FilterSegmentation
    roi_patterns = {"ROI1": ".*1", "ROI2": ".*2"}
    filter_seg = FilterSegmentation(roi_patterns)

    # Call the FilterSegmentation instance
    filtered_seg = filter_seg(reference_image[0], seg, {})

    # Assert the filtered segmentation has the expected properties
    assert isinstance(filtered_seg, sitk.Image)
    assert filtered_seg.GetSize() == reference_image[0].GetSize()
    assert filtered_seg.GetSpacing() == reference_image[1]
    assert filtered_seg.GetOrigin() == reference_image[2]
    assert filtered_seg.GetDirection() == reference_image[3]
    assert filtered_seg.GetPixelID() == sitk.sitkUInt8

    # Assert the filtered segmentation contains only the desired labels
    filtered_arr = sitk.GetArrayFromImage(filtered_seg)
    assert filtered_arr.max() == 1
    assert filtered_arr.min() == 0
    assert filtered_arr.sum() == 20
    

def test_filter_segmentation_with_op():
    # Create a test segmentation
    seg = sitk.Image(reference_image[0].GetSize(), sitk.sitkUInt8)
    seg.SetSpacing(reference_image[1])
    seg.SetOrigin(reference_image[2])
    seg.SetDirection(reference_image[3])
    seg_arr = sitk.GetArrayFromImage(seg)
    seg_arr[30:40, 30:40, 30:40] = 2
    seg_arr[60:70, 60:70, 60:70] = 3
    seg = sitk.GetImageFromArray(seg_arr)

    # Create a test instance of FilterSegmentation
    roi_patterns = {"ROI1": ".*1", "ROI2": ".*2"}
    filter_seg = FilterSegmentation(roi_patterns)

    # Call the FilterSegmentation instance
    filtered_seg = filter_seg(reference_image[0], seg, {})

    # Assert the filtered segmentation has the expected properties
    assert isinstance(filtered_seg, sitk.Image)
    assert filtered_seg.GetSize() == reference_image[0].GetSize()
    assert filtered_seg.GetSpacing() == reference_image[1]
    assert filtered_seg.GetOrigin() == reference_image[2]
    assert filtered_seg.GetDirection() == reference_image[3]
    assert filtered_seg.GetPixelID() == sitk.sitkUInt8

    # Assert the filtered segmentation contains only the desired labels
    filtered_arr = sitk.GetArrayFromImage(filtered_seg)
    assert filtered_arr.max() == 2
    assert filtered_arr.min() == 0
    assert filtered_arr.sum() == 20

@pytest.fixture
def image_subject_file_output(tmp_path):
    # Create a test instance of ImageSubjectFileOutput
    root_directory = str(tmp_path)
    filename_format = "{subject_id}.nii.gz"
    create_dirs = True
    compress = True
    return ImageSubjectFileOutput(root_directory, filename_format, create_dirs, compress)

def test_image_subject_file_output(image_subject_file_output):
    # Assert the attributes of ImageSubjectFileOutput instance
    assert image_subject_file_output.root_directory == str(tmp_path)
    assert image_subject_file_output.filename_format == "{subject_id}.nii.gz"
    assert image_subject_file_output.create_dirs == True
    assert image_subject_file_output.compress == True

    # Assert the writer attribute of ImageSubjectFileOutput instance
    assert isinstance(image_subject_file_output.writer, BaseSubjectWriter)
    assert image_subject_file_output.writer.root_directory == str(tmp_path)
    assert image_subject_file_output.writer.filename_format == "{subject_id}.nii.gz"
    assert image_subject_file_output.writer.create_dirs == True
    assert image_subject_file_output.writer.compress == True

import pytest
import SimpleITK as sitk
from imgtools.ops import FilterSegmentation, ImageAutoOutput

@pytest.fixture
def reference_image():
    # Create a reference image for testing
    size = (100, 100, 100)
    spacing = (1.0, 1.0, 1.0)
    origin = (0.0, 0.0, 0.0)
    direction = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
    return sitk.Image(size, sitk.sitkFloat32), spacing, origin, direction

def test_filter_segmentation(reference_image):
    # Create a test segmentation
    seg = sitk.Image(reference_image[0].GetSize(), sitk.sitkUInt8)
    seg.SetSpacing(reference_image[1])
    seg.SetOrigin(reference_image[2])
    seg.SetDirection(reference_image[3])
    seg_arr = sitk.GetArrayFromImage(seg)
    seg_arr[50:70, 50:70, 50:70] = 1
    seg = sitk.GetImageFromArray(seg_arr)

    # Create a test instance of FilterSegmentation
    roi_patterns = {"ROI1": ".*1", "ROI2": ".*2"}
    filter_seg = FilterSegmentation(roi_patterns)

    # Call the FilterSegmentation instance
    filtered_seg = filter_seg(reference_image[0], seg, {})

    # Assert the filtered segmentation has the expected properties
    assert isinstance(filtered_seg, sitk.Image)
    assert filtered_seg.GetSize() == reference_image[0].GetSize()
    assert filtered_seg.GetSpacing() == reference_image[1]
    assert filtered_seg.GetOrigin() == reference_image[2]
    assert filtered_seg.GetDirection() == reference_image[3]
    assert filtered_seg.GetPixelID() == sitk.sitkUInt8

    # Assert the filtered segmentation contains only the desired labels
    filtered_arr = sitk.GetArrayFromImage(filtered_seg)
    assert filtered_arr.max() == 1
    assert filtered_arr.min() == 0
    assert filtered_arr.sum() == 20
    

def test_filter_segmentation_with_op():
    # Create a test segmentation
    seg = sitk.Image(reference_image[0].GetSize(), sitk.sitkUInt8)
    seg.SetSpacing(reference_image[1])
    seg.SetOrigin(reference_image[2])
    seg.SetDirection(reference_image[3])
    seg_arr = sitk.GetArrayFromImage(seg)
    seg_arr[30:40, 30:40, 30:40] = 2
    seg_arr[60:70, 60:70, 60:70] = 3
    seg = sitk.GetImageFromArray(seg_arr)

    # Create a test instance of FilterSegmentation
    roi_patterns = {"ROI1": ".*1", "ROI2": ".*2"}
    filter_seg = FilterSegmentation(roi_patterns)

    # Call the FilterSegmentation instance
    filtered_seg = filter_seg(reference_image[0], seg, {})

    # Assert the filtered segmentation has the expected properties
    assert isinstance(filtered_seg, sitk.Image)
    assert filtered_seg.GetSize() == reference_image[0].GetSize()
    assert filtered_seg.GetSpacing() == reference_image[1]
    assert filtered_seg.GetOrigin() == reference_image[2]
    assert filtered_seg.GetDirection() == reference_image[3]
    assert filtered_seg.GetPixelID() == sitk.sitkUInt8

    # Assert the filtered segmentation contains only the desired labels
    filtered_arr = sitk.GetArrayFromImage(filtered_seg)
    assert filtered_arr.max() == 2
    assert filtered_arr.min() == 0
    assert filtered_arr.sum() == 20

@pytest.fixture
def image_subject_file_output(tmp_path):
    # Create a test instance of ImageSubjectFileOutput
    root_directory = str(tmp_path)
    filename_format = "{subject_id}.nii.gz"
    create_dirs = True
    compress = True
    return ImageSubjectFileOutput(root_directory, filename_format, create_dirs, compress)

def test_image_subject_file_output(image_subject_file_output):
    # Assert the attributes of ImageSubjectFileOutput instance
    assert image_subject_file_output.root_directory == str(tmp_path)
    assert image_subject_file_output.filename_format == "{subject_id}.nii.gz"
    assert image_subject_file_output.create_dirs == True
    assert image_subject_file_output.compress == True

    # Assert the writer attribute of ImageSubjectFileOutput instance
    assert isinstance(image_subject_file_output.writer, BaseSubjectWriter)
    assert image_subject_file_output.writer.root_directory == str(tmp_path)
    assert image_subject_file_output.writer.filename_format == "{subject_id}.nii.gz"
    assert image_subject_file_output.writer.create_dirs == True
    assert image_subject_file_output.writer.compress == True

def test_image_auto_output(tmp_path):
    # Create a test instance of ImageAutoOutput
    root_directory = str(tmp_path)
    output_streams = ["modality1", "modality2", "modality3"]
    image_auto_output = ImageAutoOutput(root_directory, output_streams)

    # Call the ImageAutoOutput instance
    subject_id = "subject1"
    img = sitk.Image(reference_image[0].GetSize(), sitk.sitkFloat32)
    output_stream = "modality1"
    image_auto_output(subject_id, img, output_stream)

    # Assert the output file has been created
    expected_file_path = tmp_path / "subject1" / "modality1.nii.gz"
    assert expected_file_path.exists()

    # Call the ImageAutoOutput instance with inference mode
    inference_image_auto_output = ImageAutoOutput(root_directory, output_streams, inference=True)
    inference_output_stream = "modality2"
    image_auto_output(subject_id, img, inference_output_stream)

    # Assert the output file with modality index has been created
    expected_inference_file_path = tmp_path / "modality2" / "subject1_0.nii.gz"
    assert expected_inference_file_path.exists()

    # Call the ImageAutoOutput instance with nnunet_info
    nnunet_info = {"label_or_image": "labels", "train_or_test": "Tr"}
    nnunet_image_auto_output = ImageAutoOutput(root_directory, output_streams, nnunet_info=nnunet_info)
    nnunet_output_stream = "modality3"
    image_auto_output(subject_id, img, nnunet_output_stream, nnunet_info=nnunet_info)

    # Assert the output file with label_or_image and train_or_test has been created
    expected_nnunet_file_path = tmp_path / "labelsTr" / "subject1_0.nii.gz"
    assert expected_nnunet_file_path.exists()