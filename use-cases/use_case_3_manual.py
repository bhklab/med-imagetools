import os, warnings, time, gc, datetime, glob
import pandas as pd
from use_case_3_utils import *
from pathlib import Path
import multiprocessing
from argparse import ArgumentParser


def add_args(return_="parser"):

    parser = ArgumentParser()
    arg = parser.add_argument
    # can add multiple arguments from bash script...
    arg("--volume", default="OARS", help="Targes vs OARs")
    arg(
        "--site",
        default="ALL",
        help="Only export contours for patient with set primary site...",
    )
    arg("--dataset", default="radcure", help="Preprocessing dataset as...?")

    if return_ == "parser":
        return parser
    else:
        args = parser.parse_args()
        return args


# Lightning Specific GPU Args
# from joblib import Parallel, delayed

args = add_args(return_="args")
dataset = args.dataset  # "radcure"
ts = time.time()

date = datetime.datetime.fromtimestamp(ts).strftime("%Y_%m_%d_%H%M%S")
root = Path(f"/cluster/home/jmarsill/EXPORT_{date}")
root_bad = Path(f"/cluster/home/jmarsill/EXPORT_{date}/bad")

# root_data = Path(f"/cluster/home/jmarsill/EXPORT_{date}/data")
# root.mkdir(exist_ok=True, parents=True)
# root_bad.mkdir(exist_ok=True, parents=True)
# root_data.mkdir(exist_ok=True, parents=True)


def save_bad(patient, save_path):

    bad_patient_files = [patient]
    df = pd.DataFrame(bad_patient_files, columns=["Bad_IMGs"])
    df.to_csv(f"{str(save_path)}/{patient}.csv", index=False)
    print(f"{patient} has a buggy in its tummy")


def working():
    laptop = "C://Users/Sejin/Documents/SegmentHN/"  # FOR LAPTOP
    server = "/cluster/home/sejinkim/SegmentHN/"  # FOR H4H
    joeServer = "/cluster/home/jmarsill/SegmentHN/process/"
    wkdir = laptop if os.path.isdir(laptop) else server
    try:
        os.chdir(wkdir)
        return wkdir

    except:
        os.chdir(joeServer)
        return joeServer


wkdir = working()
print(f"Working on: {wkdir}")
print(f"Starting to process dataset {dataset}")

# process/config/processing-opc1.yml
# process/config/roi_exceptions_opc1.yaml
config, exceptions = getConfig(wkdir, dataset)
print(config)
print(exceptions)
inputPath = config["DATA_RAW"]
outputPath = config["DATA_OUTPUT"]


def process(folder, bad_path=root_bad, extract=args.volume):
    # processes DICOM to numpy PER PATIENT
    temp, bad = [], ""
    # try:
    print(folder)
    startTime = time.time()
    inputFolder = inputPath + folder
    sub_dir = os.listdir(inputFolder)

    if len(sub_dir) < 2:

        if dataset == "radcure":
            inputFolder += "/" + sub_dir[0]

        if extract == "OARS":

            rois = [
                "GTV",
                "BRAIN",
                "BSTEM",
                "SPCOR",
                "ESOPH",
                "LARYNX",
                "MAND",
                "POSTCRI",
                "LPAR",
                "RPAR",
                "LACOU",
                "RACOU",
                "LLAC",
                "RLAC",
                "RRETRO",
                "LRETRO",
                "RPLEX",
                "LPLEX",
                "LLENS",
                "RLENS",
                "LEYE",
                "REYE",
                "LOPTIC",
                "ROPTIC",
                "LSMAN",
                "RSMAN",
                "CHIASM",
                "LIPS",
                "OCAV",
                "IPCM",
                "SPCM",
                "MPCM",
            ]

        elif extract == "TARGETS":

            rois = [
                "EXTERNAL",
                "GTV",
                "LNECK",
                "RNECK",
                "LOWRCTV",
                "MIDRCTV",
                "HIGHRCTV",
            ]

        else:

            rois = ["EXTERNAL", "GTV"]

        dicom = Dicom(inputFolder, dataset=dataset, rois=rois, resample=True)

        # rois=  ['BSTEM', 'ESOPH', 'LARYNX',
        # 'POSTCRI', 'CHIASM', 'LLAC', 'RLAC', 'LLENS', 'RLENS', 'LEYE',
        # 'REYE', 'LOPTIC', 'ROPTIC', 'LPAR', 'RPAR', 'SPCOR', 'MAND',
        # 'LSMAN', 'RSMAN', 'LACOU', 'RACOU',  'LIPS']
        # rois = ['EXTERNAL', 'CTV', 'GTV', 'LNECK', 'RNECK']
        # dicom.export (outputPath, folder, exclude = ['img'], mode="numpy")

        warnings.warn(f"Saving {folder} in {outputPath}")
        dicom.export(
            outputPath, folder, exclude=["masks_save", "img"], mode="itk", slices=False,
        )
        temp = dicom.roi_select
        print(dicom.spacing, dicom.origin)
        gc.collect()

    else:
        warnings.warn(f"More than one plan/folders found in {folder}...")

    # except Exception as e:
    #
    #     warnings.warn ("Something bad happened...")
    #     warnings.warn(e)
    #     print(e)
    #     bad = folder
    # save_bad(folder, f'{str(bad_path)}')

    endTime = time.time()
    total_time = startTime - endTime
    print("Total Processing Time:", total_time)

    return bad, folder, temp


def main(inputPath, outputPath, exception_dict):

    args = add_args(return_="args")
    start = time.time()
    print("hi", gc.isenabled())
    # print (inputPath, outputPath, exception_dict)
    # get contours data types, we're looking for CTV & L/R CTV
    dicom_folders = get_immediate_subdirectories(inputPath)
    dicom_folders = sorted(dicom_folders)
    dicom_folders = [str(i) for i in dicom_folders]
    print("Total:", len(dicom_folders))

    try:
        # if the masks are already processed, do not recompute...
        # completed = os.listdir (outputPath + "/masks")
        # this works regularly, just debugging...
        completed = glob.glob(outputPath + "/masks/*.nrrd")
        # should be outputPath..
        # completed = glob.glob('/cluster/projects/radiomics/Temp/NODES/masks/*.nrrd')
        completed = [i.split("/")[-1].partition(".")[0] for i in completed]
        print(f"Already Completed {len(completed)} images.")

    except:
        completed = []

    dicom_folders = [i for i in dicom_folders if i not in completed]
    print(f"First value found: {dicom_folders[0]}")
    # select dicom folders from specific disease site
    # Nasopharynx study about guideline compliance
    # select_site = False
    site = args.site
    print("site: ", args.site)
    # "Nasopharynx"
    vals = ["ALL", "CUSTOM"]
    if site not in vals:
        data = pd.read_csv(
            "/cluster/home/jmarsill/Lightning/data/valid_mrns_by_dssite_new2.csv"
        )
        folders = data[site]
        folders = [str(int(x)) for x in folders if str(x) != "nan"]
        dicom_folders = [i for i in dicom_folders if str(int(i)) in folders]
        print(f"Number of patients in {site} is {len(dicom_folders)}.")

    if site == "CUSTOM":

        completed = glob.glob(outputPath + "/img/*.nrrd")
        # should be outputPath..
        # completed = glob.glob('/cluster/projects/radiomics/Temp/NODES/masks/*.nrrd')
        completed = [i.split("/")[-1].partition(".")[0] for i in completed]
        print(f"Already Completed {len(completed)} images.")

        dicom_folders = [i for i in dicom_folders if i not in completed]
        dicom_folders = [i for i in folders if i not in dicom_folders]
        # dicom_folders = [i for i in dicom_folders if str(int(i)) in folders]

    # taken from /cluster/home/jmarsill/Lightning/data/valid_mrns_by_dssite_new2.csv

    print(f"Only {len(dicom_folders)} remaining.")
    print("Done:", len(completed))
    print("To do:", len(dicom_folders))

    # num_cores = multiprocessing.cpu_count()
    # results = Parallel(n_jobs=num_cores)(delayed(process)(inputPath, outputPath, folder) for folder in dicom_folders)
    p = multiprocessing.Pool()
    results = p.map(process, dicom_folders)
    print(results)

    # save logs
    info, problem = Info(), BadFiles()
    for bad, patient, names in results:
        print(bad, patient, names)
        info.add_patient(patient, names)
        problem.add_bad(bad)

    os.makedirs(outputPath, exist_ok=True)
    info.export(outputPath)  # uh fix this lol
    problem.export(outputPath)

    print(f"Script ran for {round((time.time()-start), 2)} seconds")

    return


if __name__ == "__main__":
    main(inputPath, outputPath, exceptions)  # on desktop