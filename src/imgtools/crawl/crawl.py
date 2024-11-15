import os
import pathlib
from pydicom import dcmread
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from imgtools.logging import logger, logging
baselogging = logging.getLogger("imgtools")

def crawl_one(folder: pathlib.Path) -> dict:
    folder_path = pathlib.Path(folder)
    database = {}
    logger.info("Crawling folder...", folder=folder)
    # dicoms = glob.glob(pathlib.Path(path, "**", "*.dcm").as_posix(), recursive=True)

    dicoms = folder.rglob("*.dcm")
    for dcm in dicoms:
        dcm_path = pathlib.Path(dcm)
        # parent    = dcm_path.parent#.as_posix()
        fname = dcm_path.name
        rel_path = dcm_path.relative_to(
            folder_path.parent.parent
        )  # rel_path of dicom from folder
        rel_posix = (
            rel_path.parent.as_posix()
        )  # folder name + until parent folder of dicom
        # logger.debug("paths:", fname=fname, rel_posix=rel_posix)
        meta = dcmread(dcm, force=True, stop_before_pixels=True)
        patient = str(meta.PatientID)
        study = str(meta.StudyInstanceUID)
        series = str(meta.SeriesInstanceUID)
        instance = str(meta.SOPInstanceUID)

        (
            reference_ct,
            reference_rs,
            reference_pl,
        ) = "", "", ""
        tr, te, tesla, scan_seq, elem = "", "", "", "", ""
        try:
            orientation = str(meta.ImageOrientationPatient)  # (0020, 0037)
        except:
            orientation = ""

        try:
            orientation_type = str(
                meta.AnatomicalOrientationType
            )  # (0010, 2210)
        except:
            orientation_type = ""

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

        # MRI Tags
        try:
            tr = float(meta.RepetitionTime)
        except:
            pass
        try:
            te = float(meta.EchoTime)
        except:
            pass
        try:
            scan_seq = str(meta.ScanningSequence)
        except:
            pass
        try:
            tesla = float(meta.MagneticFieldStrength)
        except:
            pass
        try:
            elem = str(meta.ImagedNucleus)
        except:
            pass

        # Frame of Reference UIDs
        try:
            reference_frame = str(meta.FrameOfReferenceUID)
        except:
            try:
                reference_frame = str(
                    meta.ReferencedFrameOfReferenceSequence[
                        0
                    ].FrameOfReferenceUID
                )
            except:
                reference_frame = ""

        try:
            study_description = str(meta.StudyDescription)
        except:
            study_description = ""

        try:
            series_description = str(meta.SeriesDescription)
        except:
            series_description = ""

        try:
            subseries = str(meta.AcquisitionNumber)
        except:
            subseries = "default"

        if patient not in database:
            database[patient] = {}
        if study not in database[patient]:
            database[patient][study] = {"description": study_description}
        if series not in database[patient][study]:
            rel_crawl_path = rel_posix
            if meta.Modality == "RTSTRUCT":
                rel_crawl_path = os.path.join(rel_crawl_path, fname)

            database[patient][study][series] = {
                "description": series_description
            }
        if subseries not in database[patient][study][series]:
            database[patient][study][series][subseries] = {
                "instances": {},
                "instance_uid": instance,
                "modality": meta.Modality,
                "reference_ct": reference_ct,
                "reference_rs": reference_rs,
                "reference_pl": reference_pl,
                "reference_frame": reference_frame,
                "folder": rel_crawl_path,
                "orientation": orientation,
                "orientation_type": orientation_type,
                "repetition_time": tr,
                "echo_time": te,
                "scan_sequence": scan_seq,
                "mag_field_strength": tesla,
                "imaged_nucleus": elem,
                "fname": rel_path.as_posix(),  # temporary until we switch to json-based loading
            }
        database[patient][study][series][subseries]["instances"][instance] = (
            rel_path.as_posix()
        )
    
    return database


def crawl_directory(top: pathlib.Path) -> list:
    # top is the input directory in the argument parser from autotest.py
    folders = list(pathlib.Path(top).iterdir())

    with logging_redirect_tqdm([baselogging]):
        database_list = [crawl_one(folder) for folder in tqdm(folders)]

    return database_list
