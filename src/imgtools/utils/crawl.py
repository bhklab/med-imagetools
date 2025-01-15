import json
import os
import pathlib
from argparse import ArgumentParser
from collections import defaultdict
from contextlib import suppress

import pandas as pd
from joblib import Parallel, delayed
from pydicom import dcmread
from tqdm import tqdm

from imgtools.logging import logger


# fmt: off
def crawl_one(folder_path_posix: str) -> dict:
    folder_path = pathlib.Path(folder_path_posix)
    assert folder_path.is_dir(), f"{folder_path} is not a directory"

    logger.info(f"Crawling One for {folder_path}")

    # patient -> study -> series -> subseries
    database = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict))))

    # TODO: I dont think we even need to iterate through subdirs, we can just glob 
    # for dicoms in the folder_path itself

    # find all subdirectories
    subdirs = [f for f in folder_path.rglob("*") if f.is_dir()]
    logger.info(f"Found {len(subdirs)} subdirectories in {folder_path}")

    for path in subdirs:
        # find dicoms
        dicoms = [f for f in path.rglob("*.dcm")]
        logger.info(f"Found {len(dicoms)} dicoms in {path}")

        for dcm in dicoms:
            dcm_path = pathlib.Path(dcm)

            dicom_filename = dcm_path.name

            # this aims to be relative to where the ".imgtools" folder is
            dicom_relative_path = dcm_path.relative_to(
                folder_path.parent.parent
            ) 

            # folder name + until parent folder of dicom
            relative_directory_path = (
                dicom_relative_path.parent.as_posix()
            )

            meta = dcmread(dcm, force=True, stop_before_pixels=True)

            ############################################################
            # Extract metadata
            PatientID = str(meta.PatientID)
            StudyInstanceUID = str(meta.StudyInstanceUID)
            SeriesInstanceUID = str(meta.SeriesInstanceUID)
            sop_instance_uid = str(meta.SOPInstanceUID)

            StudyDescription = str(getattr(meta, "StudyDescription", ""))
            SeriesDescription = str(getattr(meta, "SeriesDescription", ""))
            subseries = str(getattr(meta, "AcquisitionNumber", "default"))

            ImageOrientationPatient = str(getattr(meta, "ImageOrientationPatient", "")) # (0020, 0037)
            AnatomicalOrientationType = str(getattr(meta, "AnatomicalOrientationType", "")) # (0010, 2210)
            
            # MRI Tags
            RepetitionTime = (
                float(getattr(meta, "RepetitionTime", 0)) 
                if hasattr(meta, "RepetitionTime") 
                else ""
            )

            EchoTime = (
                float(getattr(meta, "EchoTime", 0)) 
                if hasattr(meta, "EchoTime")
                else ""
            )

            MagneticFieldStrength = (
                float(getattr(meta, "MagneticFieldStrength", 0)) 
                if hasattr(meta, "MagneticFieldStrength") 
                else ""
            )
            ScanningSequence = str(getattr(meta, "ScanningSequence", ""))
            ImagedNucleus = str(getattr(meta, "ImagedNucleus", ""))

            # Reference CT, RS, PL
            (
                reference_ct,
                reference_rs,
                reference_pl,
            ) = "", "", ""

            # TODO: this is a mess, can we extract metadata based on modality instead 
            # of trying to catch exceptions?

            try:  # RTSTRUCT
                reference_ct = str(
                    meta.ReferencedFrameOfReferenceSequence[0]
                    .RTReferencedStudySequence[0]
                    .RTReferencedSeriesSequence[0]
                    .SeriesInstanceUID
                )
            except Exception:
                try:  # SEGMENTATION
                    reference_ct = str(
                        meta.ReferencedSeriesSequence[0].SeriesInstanceUID
                    )
                except Exception:
                    with suppress(Exception):
                        reference_rs = str(
                            meta.ReferencedStructureSetSequence[
                                0
                            ].ReferencedSOPInstanceUID
                        )
                    with suppress(Exception):
                        reference_ct = str(
                            meta.ReferencedImageSequence[0].ReferencedSOPInstanceUID
                        )
                    with suppress(Exception):
                        reference_pl = str(
                            meta.ReferencedRTPlanSequence[
                                0
                            ].ReferencedSOPInstanceUID
                        )

            # TODO: extract to helper function
            # Frame of Reference UIDs
            try:
                reference_frame = str(meta.FrameOfReferenceUID)
            except AttributeError:
                try:
                    reference_frame = str(
                        meta.ReferencedFrameOfReferenceSequence[
                            0
                        ].FrameOfReferenceUID
                    )
                except AttributeError:
                    reference_frame = ""

            if meta.Modality == "RTSTRUCT": # should we also do this for SEG? 
                dicom_folder_or_file = os.path.join(relative_directory_path, dicom_filename) # noqa
            else:
                dicom_folder_or_file = relative_directory_path 

            # TODO: just realized that for a given series+subseries, the data should be the same
            # EXCEPT for the SOPInstanceUID. 
            # This means that we can check for the series+subseries wayyy before extracting the 
            # rest of the tags, and if it exists, we can just append the SOPInstanceUID to the
            # instances list.

            # defaultdict will handle missing keys for us so we dont have to do the
            # whole `if key not in dict: dict[key] = {}` dance
            # by automatically creating the key if it doesn't exist
            database[PatientID][StudyInstanceUID]["description"] = StudyDescription
            database[PatientID][StudyInstanceUID][SeriesInstanceUID]["description"] = SeriesDescription

            database[PatientID][StudyInstanceUID][SeriesInstanceUID][subseries] = {
                'SOPInstanceUID': sop_instance_uid,
                'Modality': meta.Modality,
                'reference_ct': reference_ct,
                'reference_rs': reference_rs,
                'reference_pl': reference_pl,
                'reference_frame': reference_frame,
                'folder': dicom_folder_or_file,
                'ImageOrientationPatient': ImageOrientationPatient,
                'AnatomicalOrientationType': AnatomicalOrientationType,
                'RepetitionTime': RepetitionTime,
                'EchoTime': EchoTime,
                'ScanningSequence': ScanningSequence,
                'MagneticFieldStrength': MagneticFieldStrength,
                'ImagedNucleus': ImagedNucleus,
                'fname': dicom_relative_path.as_posix(),  # temporary until we switch to json-based loading
                'instances': defaultdict(str),
            }
            database[PatientID][StudyInstanceUID][SeriesInstanceUID][subseries]["instances"][sop_instance_uid] = (
                dicom_relative_path.as_posix()
            )

    return database


def to_df(database_dict):
    dataframe_list = []

    for patient_id, patient_dict in database_dict.items():

        for study_uid, study_dict in patient_dict.items():
            for series_key, series_dict in study_dict.items():
                if series_key == "description":  # skip description key in dict
                    continue

                for subseries_key, subseries_dict in series_dict.items():
                    if subseries_key == 'description':  # skip description key in dict
                        continue

                    data = {
                        'patient_ID': patient_id,
                        'study': study_uid,
                        'study_description': study_dict['description'],
                        'series': series_key,
                        'series_description': series_dict['description'],
                        'subseries': subseries_key,
                        'modality': subseries_dict['Modality'],
                        'instances': len(subseries_dict['instances']),
                        'instance_uid': subseries_dict['SOPInstanceUID'],
                        'reference_ct': subseries_dict['reference_ct'],
                        'reference_rs': subseries_dict['reference_rs'],
                        'reference_pl': subseries_dict['reference_pl'],
                        'reference_frame': subseries_dict['reference_frame'],
                        'folder': subseries_dict['folder'],
                        'orientation': subseries_dict['ImageOrientationPatient'],
                        'orientation_type': subseries_dict['AnatomicalOrientationType'],
                        'MR_repetition_time': subseries_dict['RepetitionTime'],
                        'MR_echo_time': subseries_dict['EchoTime'],
                        'MR_scan_sequence': subseries_dict['ScanningSequence'],
                        'MR_magnetic_field_strength': subseries_dict['MagneticFieldStrength'],
                        'MR_imaged_nucleus': subseries_dict['ImagedNucleus'],
                        'file_path': subseries_dict['fname']
                    }
                    dataframe_list.append(data)
    df = pd.DataFrame(dataframe_list)
    return df

# fmt: on
def crawl(
    top: pathlib.Path,
    n_jobs: int = -1,
    csv_path: pathlib.Path | None = None,
    json_path: pathlib.Path | None = None,
    imgtools_dir: str = ".imgtools",
) -> dict:
    folders = [f for f in pathlib.Path(top).iterdir() if f.is_dir()]
    logger.info(f"Will crawl {len(folders)} folders in {top}")

    ############################################################
    # Crawl folders
    ############################################################
    # TODO: look into using multiprocessing pool instead of joblib
    # so the tqdm progress bar works properly

    database_list: list = Parallel(n_jobs=n_jobs)(
        delayed(crawl_one)(folder.as_posix())
        for folder in tqdm(folders, desc="Crawling folders", leave=False)
    )
    logger.info("Finished crawling folders", database_list=len(database_list))

    logger.info("Converting list to dictionary")
    database_dict = {}
    for db in database_list:
        for key in db:
            if key in database_dict:
                msg = (
                    f"Patient {key} already exists in database. "
                    "This is probably due to one or more dicom files"
                    " belonging to the same patient being present in multiple folders "
                    f"within {top}. Continuing with the last instance found."
                )
                logger.warning(msg)

            database_dict[key] = db[key]

    ############################################################
    # Save as json and dataframe
    ############################################################
    # configure json path
    if json_path is None:
        json_path = top.parent / imgtools_dir / f"imgtools_{top.name}.json"

    json_path.parent.mkdir(parents=True, exist_ok=True)

    # configure csv path
    if csv_path is None:
        csv_path = top.parent / imgtools_dir / f"imgtools_{top.name}.csv"

    csv_path.parent.mkdir(parents=True, exist_ok=True)

    # Save as json
    logger.info(f"Saving as json to {json_path}")
    with json_path.open("w") as f:
        json.dump(database_dict, f, indent=4)

    # Save as dataframe
    logger.info(f"Saving as dataframe to {csv_path}")
    df = to_df(database_dict)
    df.to_csv(csv_path)

    return database_dict


if __name__ == "__main__":
    parser = ArgumentParser("Dataset DICOM Crawler")
    parser.add_argument(
        "directory", type=str, help="Top-level directory of the dataset."
    )
    parser.add_argument(
        "--n_jobs",
        type=int,
        default=os.cpu_count() - 2,
        help="Number of parallel processes for multiprocessing.",
    )

    args = parser.parse_args()
    db = crawl(args.directory, n_jobs=args.n_jobs)
    print("# patients:", len(db))
