from argparse import ArgumentParser
import os, pathlib
import glob
import json
from copy import deepcopy

import pandas as pd
from pydicom import dcmread
from tqdm import tqdm

from joblib import Parallel, delayed

def findMissingCTReference(database_df, folder):
    # Find rows in the dataset dataframe that are for RTSTRUCTS with missing reference CT values
    missingRefCTs = database_df[(database_df['reference_ct'] == '') & (database_df['modality'] == 'RTSTRUCT')]
    database_df = database_df.drop(missingRefCTs.index)

    for idx, rt in missingRefCTs.iterrows():
        rt_path = os.path.join(os.path.dirname(folder), rt['file_path'])
        # Load the RTSTRUCT again
        rt_meta = dcmread(rt_path, force=True, stop_before_pixels=True)
        # Get any reference SOP Instances from the RTSTRUCT - these will be individual slices in the CT they correspond to
        refSOPInstances = rt_meta.ReferencedFrameOfReferenceSequence[0].RTReferencedStudySequence[0].RTReferencedSeriesSequence[0].ContourImageSequence
        reference_ct_list = []
        if len(refSOPInstances) > 0:
            for idx in range(len(refSOPInstances)):
                reference_ct_list.append(refSOPInstances[idx].ReferencedSOPInstanceUID)

        # Get a new dataframe with rows for each CT reference
        updatedRTRows = pd.concat([missingRefCTs.iloc[[0]]]*len(refSOPInstances))
        updatedRTRows.reset_index(drop=True, inplace=True)  

        # Get any CTs for the patient the RTSTRUCT is from
        cts = database_df[(database_df['patient_ID'] == rt['patient_ID']) & (database_df['modality'] == 'CT')]
        
        # Check each CT to see if it has the slice with the SOP in it
        for ct in cts.itertuples():
            if reference_ct_list == []:
                print("All associations found. Exiting search.")
                break
            ct_path = os.path.join(os.path.dirname(folder), ct.folder)
            dicoms = glob.glob(pathlib.Path(ct_path, "**", "*.[Dd]cm").as_posix(), recursive=True)
            for dcm in dicoms:
                ct_meta = dcmread(dcm, specific_tags=['SOPInstanceUID', 'SeriesInstanceUID'])
                if ct_meta.SOPInstanceUID in reference_ct_list:
                    print(ct_meta.SOPInstanceUID, "is in", ct_meta.SeriesInstanceUID)
                    updatedRTRows.at[len(reference_ct_list)-1, 'reference_ct'] = ct_meta.SeriesInstanceUID
                    reference_ct_list.remove(ct_meta.SOPInstanceUID)
                    break

        if reference_ct_list != []:
            print("Some associations not found.")
        
    database_df = pd.concat([database_df, updatedRTRows], ignore_index=True)
    database_df.sort_values(by=['patient_ID', 'folder'], inplace=True)
    database_df.reset_index(drop=True, inplace=True)  

    return database_df


def crawl_one(folder):
    folder_path = pathlib.Path(folder)
    database = {}
    for path, _, _ in os.walk(folder):
        # find dicoms
        dicoms = glob.glob(pathlib.Path(path, "**", "*.[Dd]cm").as_posix(), recursive=True)
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
                    orientation = str(meta.ImageOrientationPatient) # (0020, 0037)
                except:
                    orientation = ""

                try:
                    orientation_type = str(meta.AnatomicalOrientationType) # (0010, 2210)
                except:
                    orientation_type = ""

                try: #RTSTRUCT
                    reference_ct = str(meta.ReferencedFrameOfReferenceSequence[0].RTReferencedStudySequence[0].RTReferencedSeriesSequence[0].SeriesInstanceUID)
                except: 
                    try: #SEGMENTATION
                        reference_ct = str(meta.ReferencedSeriesSequence[0].SeriesInstanceUID)
                    except:
                        try: #RTDOSE
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
                
                #MRI Tags
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

                # try:
                    

                if patient not in database:
                    database[patient] = {}
                if study not in database[patient]:
                    database[patient][study] = {'description': study_description}
                if series not in database[patient][study]:
                    rel_crawl_path  = rel_posix
                    # if meta.Modality == 'RTSTRUCT':
                    #     rel_crawl_path = os.path.join(rel_crawl_path, fname)
                    
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
                                                                   'fname': rel_path.as_posix() #temporary until we switch to json-based loading
                                                                   }
                    # If there are multiple CTs referenced for this segmentation, make an RTSTRUCT instance/row for each CT ID as different acquisition/subseries (name pending)
                    if isinstance(reference_ct, list):
                        database[patient][study][series]["default"]["reference_ct"] = reference_ct[0]
                        for n, ct_id in enumerate(reference_ct[1:]):
                            database[patient][study][series][f"{subseries}_{n+1}"] = deepcopy(database[patient][study][series]["default"])
                            database[patient][study][series][f"{subseries}_{n+1}"]["reference_ct"] = ct_id
                        
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
                if series != 'description': # skip description key in dict
                    for subseries in database_dict[pat][study][series]:
                        if subseries != 'description': # skip description key in dict
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
    #top is the input directory in the argument parser from autotest.py
    database_list = []
    folders = glob.glob(pathlib.Path(top, "*").as_posix())
    
    # This is a list of dictionaries, each dictionary is a directory containing image dirs 
    database_list = Parallel(n_jobs=n_jobs)(delayed(crawl_one)(pathlib.Path(top, folder).as_posix()) for folder in tqdm(folders))

    # convert list of dictionaries to single dictionary with each key being a patient ID
    database_dict = {}
    for db in database_list:
        for key in db:
            # If multiple directories have same patient ID, merge their information together
            if key in database_dict:
                database_dict[key] = {**database_dict[key], **db[key]}
            else:
                database_dict[key] = db[key]
    
    # Checking for empty reference CT values - this works!
    database_df = to_df(database_dict)
    missingRefCTs = database_df[(database_df['reference_ct'] == '') & (database_df['modality'] == 'RTSTRUCT')]
    if not missingRefCTs.empty:
        df = findMissingCTReference(database_df, top)
    

    # save one level above imaging folders
    parent, dataset  = os.path.split(top)

    parent_imgtools = pathlib.Path(parent, ".imgtools").as_posix()

    if not os.path.exists(parent_imgtools):
        try:
            os.makedirs(parent_imgtools)
        except:
            pass
    
    # TODO: update this to save out the database_df instead of the dict
    # save as json
    with open(pathlib.Path(parent_imgtools, f'imgtools_{dataset}.json').as_posix(), 'w') as f:
        # Can I change this to saving a dataframe instead
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
