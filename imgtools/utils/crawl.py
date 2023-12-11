from argparse import ArgumentParser
import os
import pathlib
import glob
import json
import pandas as pd
from pydicom import dcmread
from tqdm import tqdm
from joblib import Parallel, delayed


def crawl_one(folder):
    folder_path = pathlib.Path(folder)
    database = {}
    for path, _, _ in os.walk(folder):
        # find dicoms
        dicoms = glob.glob(pathlib.Path(path, "**", "*.dcm").as_posix(), recursive=True)
        # print('\n', folder, dicoms)
        # instance (slice) information
        for dcm in dicoms:
            try:
                dcm_path  = pathlib.Path(dcm)
                # parent    = dcm_path.parent#.as_posix()
                fname     = dcm_path.name
                rel_path  = dcm_path.relative_to(folder_path.parent.parent)                                        # rel_path of dicom from folder
                rel_posix = rel_path.parent.as_posix()     # folder name + until parent folder of dicom

                meta      = dcmread(dcm, force=True, stop_before_pixels=True)
                patient   = str(meta.PatientID)
                study     = str(meta.StudyInstanceUID)
                series    = str(meta.SeriesInstanceUID)
                instance  = str(meta.SOPInstanceUID)

                reference_ct, reference_rs, reference_pl,  = "", "", ""
                tr, te, tesla, scan_seq, elem = "", "", "", "", ""
                try:
                    orientation = str(meta.ImageOrientationPatient)  # (0020, 0037)
                except:
                    orientation = ""

                try:
                    orientation_type = str(meta.AnatomicalOrientationType)  # (0010, 2210)
                except:
                    orientation_type = ""

                try:  # RTSTRUCT
                    reference_ct = str(meta.ReferencedFrameOfReferenceSequence[0].RTReferencedStudySequence[0].RTReferencedSeriesSequence[0].SeriesInstanceUID)
                except: 
                    try: # SEGMENTATION
                        reference_ct = str(meta.ReferencedSeriesSequence[0].SeriesInstanceUID)
                    except:
                        try:  # RTDOSE
                            reference_rs = str(meta.ReferencedStructureSetSequence[0].ReferencedSOPInstanceUID)
                        except:
                            pass
                        try:
                            reference_ct = str(meta.ReferencedImageSequence[0].ReferencedSOPInstanceUID)
                        except:
                            pass
                        try:
                            reference_pl = str(meta.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID)
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
                        reference_frame = str(meta.ReferencedFrameOfReferenceSequence[0].FrameOfReferenceUID)
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
                    database[patient][study] = {'description': study_description}
                if series not in database[patient][study]:
                    rel_crawl_path = rel_posix
                    if meta.Modality == 'RTSTRUCT':
                        rel_crawl_path = os.path.join(rel_crawl_path, fname)
                    
                    database[patient][study][series] = {'description': series_description}
                if subseries not in database[patient][study][series]:
                    database[patient][study][series][subseries] = {'instances': {},
                                                                   'instance_uid': instance,
                                                                   'modality': meta.Modality,
                                                                   'reference_ct': reference_ct,
                                                                   'reference_rs': reference_rs,
                                                                   'reference_pl': reference_pl,
                                                                   'reference_frame': reference_frame,
                                                                   'folder': rel_crawl_path,
                                                                   'orientation': orientation,
                                                                   'orientation_type': orientation_type,
                                                                   'repetition_time':tr,
                                                                   'echo_time':te,
                                                                   'scan_sequence': scan_seq,
                                                                   'mag_field_strength': tesla,
                                                                   'imaged_nucleus': elem,
                                                                   'fname': rel_path.as_posix()  # temporary until we switch to json-based loading
                                                                   }
                database[patient][study][series][subseries]['instances'][instance] = rel_path.as_posix()
            except Exception as e:
                print(folder, e)
                pass
    
    return database


def to_df(database_dict):
    df = pd.DataFrame()
    for pat in database_dict:
        for study in database_dict[pat]:
            for series in database_dict[pat][study]:
                if series != 'description':  # skip description key in dict
                    for subseries in database_dict[pat][study][series]:
                        if subseries != 'description':  # skip description key in dict
                            columns = ['patient_ID', 'study', 'study_description', 
                                       'series', 'series_description', 'subseries', 'modality', 
                                       'instances', 'instance_uid', 
                                       'reference_ct', 'reference_rs', 'reference_pl', 'reference_frame', 'folder',
                                       'orientation', 'orientation_type', 'MR_repetition_time', 'MR_echo_time', 
                                       'MR_scan_sequence', 'MR_magnetic_field_strength', 'MR_imaged_nucleus', 'file_path']
                            values = [pat, study, database_dict[pat][study]['description'], 
                                      series, database_dict[pat][study][series]['description'], 
                                      subseries, database_dict[pat][study][series][subseries]['modality'], 
                                      len(database_dict[pat][study][series][subseries]['instances']), database_dict[pat][study][series][subseries]['instance_uid'], 
                                      database_dict[pat][study][series][subseries]['reference_ct'], database_dict[pat][study][series][subseries]['reference_rs'], 
                                      database_dict[pat][study][series][subseries]['reference_pl'], database_dict[pat][study][series][subseries]['reference_frame'], database_dict[pat][study][series][subseries]['folder'],
                                      database_dict[pat][study][series][subseries]['orientation'], database_dict[pat][study][series][subseries]['orientation_type'],
                                      database_dict[pat][study][series][subseries]['repetition_time'], database_dict[pat][study][series][subseries]['echo_time'],
                                      database_dict[pat][study][series][subseries]['scan_sequence'], database_dict[pat][study][series][subseries]['mag_field_strength'], database_dict[pat][study][series][subseries]['imaged_nucleus'],
                                      database_dict[pat][study][series][subseries]['fname']
                                      ]

                            df_add = pd.DataFrame([values], columns=columns)
                            df = pd.concat([df, df_add], ignore_index=True)
    return df


def crawl(top, 
          n_jobs: int = -1):
    # top is the input directory in the argument parser from autotest.py
    database_list = []
    folders = glob.glob(pathlib.Path(top, "*").as_posix())
    
    database_list = Parallel(n_jobs=n_jobs)(delayed(crawl_one)(pathlib.Path(top, folder).as_posix()) for folder in tqdm(folders))

    # convert list to dictionary
    database_dict = {}
    for db in database_list:
        for key in db:
            database_dict[key] = db[key]
    
    # save one level above imaging folders
    parent, dataset  = os.path.split(top)

    parent_imgtools = pathlib.Path(parent, ".imgtools").as_posix()

    if not os.path.exists(parent_imgtools):
        try:
            os.makedirs(parent_imgtools)
        except:
            pass
    
    # save as json
    with open(pathlib.Path(parent_imgtools, f'imgtools_{dataset}.json').as_posix(), 'w') as f:
        json.dump(database_dict, f, indent=4)
    
    # save as dataframe
    df = to_df(database_dict)
    df_path = pathlib.Path(parent_imgtools, f'imgtools_{dataset}.csv').as_posix()
    df.to_csv(df_path)
    
    return database_dict


if __name__ == "__main__":
    parser = ArgumentParser("Dataset DICOM Crawler")
    parser.add_argument("directory",
                        type=str,
                        help="Top-level directory of the dataset.")
    parser.add_argument("--n_jobs",
                        type=int,
                        default=16,
                        help="Number of parallel processes for multiprocessing.")

    args = parser.parse_args()
    db = crawl(args.directory, n_jobs=args.n_jobs)
    print("# patients:", len(db))
