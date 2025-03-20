from imgtools.io.writers import (
    BaseSubjectWriter,
    BaseWriter,
    HDF5Writer,
    ImageFileWriter,
    MetadataWriter,
    NumpyWriter,
    SegNrrdWriter,
)
import SimpleITK as sitk

from ..ops.ops import BaseOutput
from imgtools.loggers import logger
import pathlib
from typing import List, Optional, Dict

class ImageFileOutput(BaseOutput):
    """ImageFileOutput class outputs processed images as one of the image file formats.

    Parameters
    ----------
    root_directory: str
        Root directory where the processed image files will be stored.

    filename_format: str, optional
        The filename template.
        Set to be {subject_id}.nrrd as default.
        {subject_id} will be replaced by each subject's ID at runtime.

    create_dirs: bool, optional
        Specify whether to create an output directory if it does not exit.
        Set to be True as default.

    compress: bool, optional
        Specify whether to enable compression for NRRD format.
        Set to be true as default.
    """

    def __init__(
        self,
        root_directory: str,
        filename_format: Optional[str] = "{subject_id}.nrrd",
        create_dirs: Optional[bool] = True,
        compress: Optional[bool] = True,
    ):
        self.root_directory = root_directory
        self.filename_format = filename_format
        self.create_dirs = create_dirs
        self.compress = compress

        if ".seg" in filename_format:  # from .seg.nrrd bc it is now .nii.gz
            writer_class = SegNrrdWriter
        else:
            writer_class = ImageFileWriter

        writer = writer_class(
            self.root_directory, self.filename_format, self.create_dirs, self.compress
        )

        super().__init__(writer)


# Resampling ops
class ImageSubjectFileOutput(BaseOutput):
    def __init__(
        self,
        root_directory: str,
        filename_format: Optional[str] = "{subject_id}.nii.gz",
        create_dirs: Optional[bool] = True,
        compress: Optional[bool] = True,
    ):
        self.root_directory = root_directory
        self.filename_format = filename_format
        self.create_dirs = create_dirs
        self.compress = compress

        writer = BaseSubjectWriter(
            self.root_directory, self.filename_format, self.create_dirs, self.compress
        )

        super().__init__(writer)
class ImageAutoOutput:
    """
    Wrapper class around ImageFileOutput. This class supports multiple modalities writers and calls ImageFileOutput for writing the files

    Parameters
    ----------
    root_directory: str
        The directory where all the processed files will be stored in the form of nrrd

    output_streams: List[str]
        The modalties that should be stored. This is typically equal to the column names of the table returned after graph querying. Examples is provided in the
        dictionary file_name
    """

    def __init__(
        self,
        root_directory: str,
        output_streams: List[str],
        nnunet_info: Dict = None,
        inference: bool = False,
    ):
        self.output = {}
        for colname in output_streams:
            # Not considering colnames ending with alphanumeric
            colname_process = ("_").join(
                [item for item in colname.split("_") if not item.isnumeric()]
            )
            colname_process = colname  # temproary force #
            if not nnunet_info and not inference:
                self.output[colname_process] = ImageSubjectFileOutput(
                    pathlib.Path(
                        root_directory, "{subject_id}", colname_process.split(".")[0]
                    ).as_posix(),
                    filename_format="{}.nii.gz".format(colname_process),
                )
            elif inference:
                self.output[colname_process] = ImageSubjectFileOutput(
                    root_directory,
                    filename_format="{subject_id}_{modality_index}.nii.gz",
                )
            else:
                self.output[colname_process] = ImageSubjectFileOutput(
                    pathlib.Path(
                        root_directory, "{label_or_image}{train_or_test}"
                    ).as_posix(),
                    filename_format="{subject_id}_{modality_index}.nii.gz",
                )

    def __call__(
        self,
        subject_id: str,
        img: sitk.Image,
        output_stream,
        is_mask: bool = False,
        mask_label: Optional[str] = "",
        label_or_image: str = "images",
        train_or_test: str = "Tr",
        nnunet_info: Dict = None,
    ):
        self.output[output_stream](
            subject_id,
            img,
            is_mask=is_mask,
            mask_label=mask_label,
            label_or_image=label_or_image,
            train_or_test=train_or_test,
            nnunet_info=nnunet_info,
        )


class MetadataOutput(BaseOutput):
    """MetadataOutput class outputs the metadata of processed image files in .json format.

    Parameters
    ----------
    root_directory: str
        Root directory where the processed .json file will be stored.

    filename_format: str, optional
        The filename template.
        Set to be {subject_id}.json as default.
        {subject_id} will be replaced by each subject's ID at runtime.

    create_dirs: bool, optional
        Specify whether to create an output directory if it does not exit.
        Set to be True as default.

    """

    def __init__(
        self,
        root_directory: str,
        filename_format: Optional[str] = "{subject_id}.json",
        create_dirs: Optional[bool] = True,
    ):
        self.root_directory = root_directory
        self.filename_format = filename_format
        self.create_dirs = create_dirs
        writer = MetadataWriter(
            self.root_directory, self.filename_format, self.create_dirs
        )
        super().__init__(writer)


class NumpyOutput(BaseOutput):
    """NumpyOutput class processed images as NumPy files.

    Parameters
    ----------
    root_directory: str
        Root directory where the processed NumPy files will be stored.

    filename_format: str, optional
        The filename template.
        Set to be {subject_id}.npy as default.
        {subject_id} will be replaced by each subject's ID at runtime.

    create_dirs: bool, optional
        Specify whether to create an output directory if it does not exit.
        Set to be True as default.

    """

    def __init__(
        self,
        root_directory: str,
        filename_format: Optional[str] = "{subject_id}.npy",
        create_dirs: Optional[bool] = True,
    ):
        self.root_directory = root_directory
        self.filename_format = filename_format
        self.create_dirs = create_dirs
        writer = NumpyWriter(
            self.root_directory, self.filename_format, self.create_dirs
        )
        super().__init__(writer)


class HDF5Output(BaseOutput):
    """HDF5Output class outputs the processed image data in HDF5 format.

    Parameters
    ----------
    root_directory: str
        Root directory where the processed .h5 file will be stored.

    filename_format: str, optional
        The filename template.
        Set to be {subject_id}.h5 as default.
        {subject_id} will be replaced by each subject's ID at runtime.

    create_dirs: bool, optional
        Specify whether to create an output directory if it does not exit.
        Set to be True as default.

    save_geometry: bool, optional
        Specify whether to save geometry data.
        Set to be True as default.

    """

    def __init__(
        self,
        root_directory: str,
        filename_format: Optional[str] = "{subject_id}.h5",
        create_dirs: Optional[bool] = True,
        save_geometry: Optional[bool] = True,
    ):
        self.root_directory = root_directory
        self.filename_format = filename_format
        self.create_dirs = create_dirs
        self.save_geometry = save_geometry
        writer = HDF5Writer(
            self.root_directory,
            self.filename_format,
            self.create_dirs,
            self.save_geometry,
        )
        super().__init__(writer)