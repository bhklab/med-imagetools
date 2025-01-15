import json
import os
import pathlib
from argparse import ArgumentParser
from collections import defaultdict

import pandas as pd
from joblib import Parallel, delayed
from pydicom import dcmread
from tqdm import tqdm

from imgtools.logging import logger


# fmt: off
def crawl_one(folder_path: pathlib.Path) -> dict:
    folder_path = pathlib.Path(folder_path)
    assert folder_path.is_dir(), f"{folder_path} is not a directory"

    logger.info(f"Crawling One for {folder_path}")

    # patient -> study -> series -> subseries
    database = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict))))
    for path in folder_path.iterdir():
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
            patient = str(meta.PatientID)
            study = str(meta.StudyInstanceUID)
            series = str(meta.SeriesInstanceUID)
            sop_instance_uid = str(meta.SOPInstanceUID)

            study_description = str(getattr(meta, "StudyDescription", ""))
            series_description = str(getattr(meta, "SeriesDescription", ""))
            subseries = str(getattr(meta, "AcquisitionNumber", "default"))

            orientation = str(getattr(meta, "ImageOrientationPatient", "")) # (0020, 0037)
            orientation_type = str(getattr(meta, "AnatomicalOrientationType", "")) # (0010, 2210)
            
            # MRI Tags
            tr = float(getattr(meta, "RepetitionTime", 0)) if hasattr(meta, "RepetitionTime") else ""
            te = float(getattr(meta, "EchoTime", 0)) if hasattr(meta, "EchoTime") else ""
            tesla = float(getattr(meta, "MagneticFieldStrength", 0)) if hasattr(meta, "MagneticFieldStrength") else ""
            scan_seq = str(getattr(meta, "ScanningSequence", ""))
            elem = str(getattr(meta, "ImagedNucleus", ""))

            # Reference CT, RS, PL
            (
                reference_ct,
                reference_rs,
                reference_pl,
            ) = "", "", ""
            try:  # RTSTRUCT
                reference_ct = str(
                    meta.ReferencedFrameOfReferenceSequence[0]
                    .RTReferencedStudySequence[0]
                    .RTReferencedSeriesSequence[0]
                    .SeriesInstanceUID
                )
            except:
                try:  # SEGMENTATION
                    reference_ct = str(
                        meta.ReferencedSeriesSequence[0].SeriesInstanceUID
                    )
                except:
                    try:  # RTDOSE
                        reference_rs = str(
                            meta.ReferencedStructureSetSequence[
                                0
                            ].ReferencedSOPInstanceUID
                        )
                    except:
                        pass
                    try:
                        reference_ct = str(
                            meta.ReferencedImageSequence[0].ReferencedSOPInstanceUID
                        )
                    except:
                        pass
                    try:
                        reference_pl = str(
                            meta.ReferencedRTPlanSequence[
                                0
                            ].ReferencedSOPInstanceUID
                        )
                    except:
                        pass

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
                dicom_folder_or_file = os.path.join(relative_directory_path, dicom_filename)
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
            database[patient][study]["description"] = study_description
            database[patient][study][series]["description"] = series_description

            database[patient][study][series][subseries] = {
                'instance_uid': sop_instance_uid,
                'modality': meta.Modality,
                'reference_ct': reference_ct,
                'reference_rs': reference_rs,
                'reference_pl': reference_pl,
                'reference_frame': reference_frame,
                'folder': dicom_folder_or_file,
                'orientation': orientation,
                'orientation_type': orientation_type,
                'repetition_time':tr,
                'echo_time':te,
                'scan_sequence': scan_seq,
                'mag_field_strength': tesla,
                'imaged_nucleus': elem,
                'fname': dicom_relative_path.as_posix(),  # temporary until we switch to json-based loading
                'instances': defaultdict(str),
            }
            database[patient][study][series][subseries]["instances"][sop_instance_uid] = (
                dicom_relative_path.as_posix()
            )

    return database


def to_df(database_dict):
    df = pd.DataFrame()
    columns = ['patient_ID', 'study', 'study_description',  # noqa
                                       'series', 'series_description', 'subseries', 'modality', 
                                       'instances', 'instance_uid', 
                                       'reference_ct', 'reference_rs', 'reference_pl', 'reference_frame', 'folder',
                                       'orientation', 'orientation_type', 'MR_repetition_time', 'MR_echo_time', 
                                       'MR_scan_sequence', 'MR_magnetic_field_strength', 'MR_imaged_nucleus', 'file_path']
    for pat in database_dict:
        for study in database_dict[pat]:
            for series in database_dict[pat][study]:
                if series == "description":  # skip description key in dict
                    continue
                for subseries in database_dict[pat][study][series]:
                    if subseries == 'description':  # skip description key in dict
                        continue
                    values = [
                        pat, 
                        study, 
                        database_dict[pat][study]['description'], # noqa
                        series, 
                        database_dict[pat][study][series]['description'], 
                        subseries, 
                        database_dict[pat][study][series][subseries]['modality'], 
                        len(database_dict[pat][study][series][subseries]['instances']), 
                        database_dict[pat][study][series][subseries]['instance_uid'], 
                        database_dict[pat][study][series][subseries]['reference_ct'],
                        database_dict[pat][study][series][subseries]['reference_rs'], 
                        database_dict[pat][study][series][subseries]['reference_pl'], 
                        database_dict[pat][study][series][subseries]['reference_frame'], 
                        database_dict[pat][study][series][subseries]['folder'],
                        database_dict[pat][study][series][subseries]['orientation'], 
                        database_dict[pat][study][series][subseries]['orientation_type'],
                        database_dict[pat][study][series][subseries]['repetition_time'], 
                        database_dict[pat][study][series][subseries]['echo_time'],
                        database_dict[pat][study][series][subseries]['scan_sequence'], 
                        database_dict[pat][study][series][subseries]['mag_field_strength'], 
                        database_dict[pat][study][series][subseries]['imaged_nucleus'],
                        database_dict[pat][study][series][subseries]['fname']
                    ]

                    df_add = pd.DataFrame([values], columns=columns)
                    df = pd.concat([df, df_add], ignore_index=True)
    return df

# fmt: on


def crawl(
    top: pathlib.Path,
    n_jobs: int = -1,
    csv_path: pathlib.Path | None = None,
    json_path: pathlib.Path | None = None,
    imgtools_dir: str = ".imgtools",
) -> dict:
    database_list = []
    # folders = glob.glob(pathlib.Path(top, "*").as_posix())
    folders = [f for f in pathlib.Path(top).iterdir() if f.is_dir()]
    logger.info(f"Will crawl {len(folders)} folders in {top}")

    database_list = Parallel(n_jobs=n_jobs)(
        delayed(crawl_one)(folder.as_posix())
        for folder in tqdm(folders, desc="Crawling folders", leave=False)
    )
    logger.info("Converting list to dictionary")
    # convert list to dictionary
    database_dict = {}
    for db in database_list:
        for key in db:
            if key in database_dict:
                msg = (
                    f"Patient {key} already exists in database. "
                    "This is probably due to one or more dicom files"
                    " belonging to the same patient being present in multiple folders "
                    f"within {top}."
                )
                logger.warning(msg)

            database_dict[key] = db[key]

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
